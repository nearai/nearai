use anyhow::{Context, Result};
use bollard::Docker;
use bollard::container::{Config, CreateContainerOptions};
use bollard::image::CreateImageOptions;
use bollard::models::{HostConfig, PortBinding};
use futures::StreamExt;
use std::collections::{HashMap, VecDeque};

pub struct RunConfig {
    provider: String,
    model: String,
    temperature: f32,
    max_tokens: u32,
    max_iterations: u32,
    env_vars: HashMap<String, String>,
}

impl RunConfig {
    pub fn new(
        provider: String,
        model: String,
        temperature: f32,
        max_tokens: u32,
        max_iterations: u32,
        env_vars: HashMap<String, String>,
    ) -> Self {
        Self {
            provider,
            model,
            temperature,
            max_tokens,
            max_iterations,
            env_vars,
        }
    }
}

pub struct Manager {
    docker: Docker,
    runner_image_name: String,
    free_cvm_ports: VecDeque<u16>,
}

impl Manager {
    pub async fn new(docker: Docker, pool_size: usize) -> Result<Self> {
        let mut manager = Self {
            docker,
            runner_image_name: "plgnai/nearai_cvm_runner".to_string(),
            free_cvm_ports: VecDeque::with_capacity(pool_size),
        };

        // Fill the CVM pool during initialization
        manager.fill_cvm_pool().await?;

        Ok(manager)
    }

    pub async fn get_cvm(&mut self) -> Result<u16> {
        let mut port_to_return = None;
        let mut index_to_remove = None;

        // First, find a working CVM
        for (i, &port) in self.free_cvm_ports.iter().enumerate() {
            let mut client = match cvm_client::CvmClient::new(
                format!("https://localhost:{}", port).as_str(),
                None,
            ) {
                Ok(client) => client,
                Err(e) => {
                    tracing::warn!("Failed to create CVM client on port {}: {}", port, e);
                    continue;
                }
            };

            match client.attest().await {
                Ok(_) => {
                    port_to_return = Some(port);
                    index_to_remove = Some(i);
                    break;
                }
                Err(e) => {
                    tracing::warn!("Failed to attest CVM on port {}: {}", port, e);
                    continue;
                }
            }
        }

        // If we found a working CVM, remove it from the pool and refill
        if let Some(port) = port_to_return {
            if let Some(index) = index_to_remove {
                self.free_cvm_ports.remove(index);
                self.fill_cvm_pool().await?;
            }
            return Ok(port);
        }

        Err(anyhow::anyhow!("No free CVM ports available"))
    }

    async fn fill_cvm_pool(&mut self) -> Result<()> {
        while self.free_cvm_ports.len() < self.free_cvm_ports.capacity() {
            let port = self.add_cvm_to_pool().await?;
            self.free_cvm_ports.push_back(port);
        }
        Ok(())
    }

    async fn add_cvm_to_pool(&self) -> Result<u16> {
        // Set up port mapping for the API (port 443)
        // We'll expose port 443 of the container to a random port on the host
        let mut exposed_ports = HashMap::new();
        exposed_ports.insert("443/tcp".to_string(), HashMap::new());

        // Create port bindings for host config
        let mut port_bindings = HashMap::new();
        // Empty HostPort means Docker will assign a random available port
        port_bindings.insert(
            "443/tcp".to_string(),
            Some(vec![PortBinding {
                host_ip: Some("0.0.0.0".to_string()),
                host_port: None,
            }]),
        );

        // Create host config with port bindings and volume mounts
        let host_config = HostConfig {
            port_bindings: Some(port_bindings),
            binds: Some(vec!["/var/run/tappd.sock:/var/run/tappd.sock".to_string()]),
            ..Default::default()
        };

        // Create container config
        let container_config = Config {
            image: Some(self.runner_image_name.clone()),
            exposed_ports: Some(exposed_ports),
            host_config: Some(host_config),
            ..Default::default()
        };

        // Create container options
        let container_options = CreateContainerOptions {
            name: format!("cvm-{}", uuid::Uuid::new_v4()),
            ..Default::default()
        };

        // Create and start the container
        let container = self
            .docker
            .create_container(Some(container_options), container_config)
            .await
            .context("Failed to create CVM container")?;

        self.docker
            .start_container::<String>(&container.id, None)
            .await
            .context("Failed to start CVM container")?;

        tracing::info!("Started CVM container with ID: {}", container.id);

        // Get container information to find the assigned host port
        let container_info = self
            .docker
            .inspect_container(&container.id, None)
            .await
            .context("Failed to inspect container")?;

        // Extract the host port that was assigned to container port 443
        if let Some(network_settings) = container_info.network_settings {
            if let Some(ports) = network_settings.ports {
                if let Some(bindings) = ports.get("443/tcp") {
                    if let Some(bindings_vec) = bindings {
                        if !bindings_vec.is_empty() {
                            let binding = &bindings_vec[0];
                            if let Some(host_port_str) = &binding.host_port {
                                if let Ok(host_port) = host_port_str.parse::<u16>() {
                                    // Store the port mapping
                                    tracing::info!("CVM is accessible on host port {}", host_port);
                                    return Ok(host_port);
                                }
                            }
                        }
                    }
                }
            }
        }

        Err(anyhow::anyhow!("Failed to get CVM port"))
    }

    pub async fn assign_cvm(
        &mut self,
        run_id: String,
        thread_id: String,
        agent_id: String,
        run_config: RunConfig,
    ) -> Result<u16> {
        // Get a free CVM
        let port = self.get_cvm().await?;

        // Configure the CVM with the provided parameters
        self.configure_cvm(port, run_id, thread_id, agent_id, run_config)
            .await?;

        Ok(port)
    }

    async fn configure_cvm(
        &self,
        port: u16,
        run_id: String,
        thread_id: String,
        agent_id: String,
        run_config: RunConfig,
    ) -> Result<()> {
        // Create a client for the CVM
        let mut client =
            cvm_client::CvmClient::new(format!("https://localhost:{}", port).as_str(), None)
                .context("Failed to create CVM client")?;

        // Perform attestation to verify the CVM
        client.attest().await.context("Failed to attest CVM")?;

        // Create the assign request
        let assign_request = cvm_client::AssignRequest {
            agent_id,
            thread_id,
            api_url: "https://api.near.ai".to_string(), // This should be configurable
            provider: run_config.provider,
            model: run_config.model,
            temperature: run_config.temperature,
            max_tokens: run_config.max_tokens,
            max_iterations: run_config.max_iterations,
            env_vars: run_config.env_vars,
        };

        // Assign the agent to the CVM
        tracing::info!(
            "Assigning agent {} to CVM on port {}",
            assign_request.agent_id,
            port
        );
        client
            .assign(assign_request)
            .await
            .context("Failed to assign agent to CVM")?;

        // Create the run request
        let run_request = cvm_client::RunRequest { run_id };

        // Run the agent on the CVM
        tracing::info!("Running agent on CVM, run_id: {}", run_request.run_id);
        client
            .run(run_request)
            .await
            .context("Failed to run agent on CVM")?;

        tracing::info!("Successfully configured and started CVM on port {}", port);

        Ok(())
    }
}

/// Start a Docker container with the specified image and configuration
pub async fn start_docker_container(
    docker: &Docker,
    image_name: &str,
    container_name: Option<&str>,
    ports: Option<HashMap<String, HashMap<(), ()>>>,
    volumes: Option<Vec<String>>,
    env_vars: Option<Vec<String>>,
) -> Result<String> {
    tracing::info!("Pulling image: {}", image_name);
    let mut create_image_stream = docker.create_image(
        Some(CreateImageOptions {
            from_image: image_name.to_string(),
            ..Default::default()
        }),
        None,
        None,
    );

    while let Some(result) = create_image_stream.next().await {
        match result {
            Ok(_) => {}
            Err(e) => tracing::error!("Error pulling image: {}", e),
        }
    }

    // Prepare container configuration
    let mut container_config = Config {
        image: Some(image_name.to_string()),
        env: env_vars,
        exposed_ports: ports,
        host_config: None,
        ..Default::default()
    };

    // Configure volume bindings if provided
    if let Some(volume_bindings) = volumes {
        let host_config = HostConfig {
            binds: Some(volume_bindings),
            ..Default::default()
        };
        container_config.host_config = Some(host_config);
    }

    // Create the container
    let container_options = match container_name {
        Some(name) => Some(CreateContainerOptions {
            name: name.to_string(),
            ..Default::default()
        }),
        None => None,
    };

    let container = docker
        .create_container(container_options, container_config)
        .await
        .context("Failed to create container")?;

    // Start the container
    docker
        .start_container::<String>(&container.id, None)
        .await
        .context("Failed to start container")?;

    tracing::info!("Container started with ID: {}", container.id);
    Ok(container.id)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[tokio::test]
    async fn test_start_docker_container() {
        // Initialize tracing for tests
        let _ = tracing_subscriber::fmt::try_init();

        // Skip test if SKIP_DOCKER_TESTS environment variable is set
        if env::var("SKIP_DOCKER_TESTS").is_ok() {
            tracing::info!("Skipping Docker test");
            return;
        }

        // Use a lightweight image for testing
        let image_name = "alpine:latest";
        let container_name: Option<&str> = Some("test-container");

        // No ports needed for this test
        let ports: Option<HashMap<String, HashMap<(), ()>>> = None;

        // No volumes needed for this test
        let volumes: Option<Vec<String>> = None;

        // Simple command to exit immediately
        let env_vars: Option<Vec<String>> = Some(vec!["TEST=true".to_string()]);

        let docker = Docker::connect_with_socket_defaults().unwrap();
        let result = start_docker_container(
            &docker,
            image_name,
            container_name,
            ports,
            volumes,
            env_vars,
        )
        .await;

        assert!(
            result.is_ok(),
            "Failed to start container: {:?}",
            result.err()
        );

        // Clean up the container after test
        if let Ok(container_id) = result {
            let _ = docker.stop_container(&container_id, None).await;
            let _ = docker.remove_container(&container_id, None).await;
        }
    }

    #[tokio::test]
    async fn test_docker_in_docker() {
        // Initialize tracing for tests
        let _ = tracing_subscriber::fmt::try_init();

        // Skip test if SKIP_DOCKER_TESTS environment variable is set
        if env::var("SKIP_DOCKER_TESTS").is_ok() {
            tracing::info!("Skipping Docker test");
            return;
        }

        // Use Docker-in-Docker image for testing
        let image_name = "docker:dind";
        let container_name: Option<&str> = Some("test-dind");

        // No ports needed for this test
        let ports: Option<HashMap<String, HashMap<(), ()>>> = None;

        // Mount Docker socket
        let volumes: Option<Vec<String>> = Some(vec![
            "/var/run/docker.sock:/var/run/docker.sock".to_string(),
        ]);

        // No environment variables needed
        let env_vars: Option<Vec<String>> = None;

        let docker = Docker::connect_with_socket_defaults().unwrap();
        let result = start_docker_container(
            &docker,
            image_name,
            container_name,
            ports,
            volumes,
            env_vars,
        )
        .await;

        assert!(
            result.is_ok(),
            "Failed to start Docker-in-Docker container: {:?}",
            result.err()
        );

        // Clean up the container after test
        if let Ok(container_id) = result {
            let _ = docker.stop_container(&container_id, None).await;
            let _ = docker.remove_container(&container_id, None).await;
        }
    }

    #[tokio::test]
    async fn test_random_port_mapping() {
        // Initialize tracing for tests
        let _ = tracing_subscriber::fmt::try_init();

        // Skip test if SKIP_DOCKER_TESTS environment variable is set
        if env::var("SKIP_DOCKER_TESTS").is_ok() {
            tracing::info!("Skipping Docker test");
            return;
        }

        // Use Nginx image for testing
        let image_name = "nginx:alpine";
        let container_name: Option<&str> = Some("test-nginx");

        // Map port 80 to a random port
        let mut port_map = HashMap::new();
        port_map.insert("80/tcp".to_string(), HashMap::new());
        let ports: Option<HashMap<String, HashMap<(), ()>>> = Some(port_map);

        // No volumes needed for this test
        let volumes: Option<Vec<String>> = None;

        // No environment variables needed
        let env_vars: Option<Vec<String>> = None;

        let docker = Docker::connect_with_socket_defaults().unwrap();
        let result = start_docker_container(
            &docker,
            image_name,
            container_name,
            ports,
            volumes,
            env_vars,
        )
        .await;

        assert!(
            result.is_ok(),
            "Failed to start Nginx container: {:?}",
            result.err()
        );

        // Get the container info to check the port mapping
        if let Ok(container_id) = &result {
            let container_info = docker.inspect_container(container_id, None).await.unwrap();

            // Verify that a port was assigned
            if let Some(network_settings) = container_info.network_settings {
                if let Some(ports) = network_settings.ports {
                    if let Some(bindings) = ports.get("80/tcp") {
                        if let Some(bindings_vec) = bindings {
                            if !bindings_vec.is_empty() {
                                let binding = &bindings_vec[0];
                                if let Some(host_port) = &binding.host_port {
                                    tracing::info!("Nginx is accessible on port {}", host_port);
                                    assert!(!host_port.is_empty(), "Host port should not be empty");
                                } else {
                                    panic!("No host port assigned");
                                }
                            } else {
                                panic!("Empty bindings vector");
                            }
                        } else {
                            panic!("No bindings vector");
                        }
                    } else {
                        panic!("No 80/tcp port mapping");
                    }
                } else {
                    panic!("No ports in network settings");
                }
            } else {
                panic!("No network settings");
            }
        }

        // Clean up the container after test
        if let Ok(container_id) = result {
            let _ = docker.stop_container(&container_id, None).await;
            let _ = docker.remove_container(&container_id, None).await;
        }
    }

    #[tokio::test]
    async fn test_fill_cvm_pool() {
        // Initialize tracing for tests
        let _ = tracing_subscriber::fmt::try_init();

        // Skip test if SKIP_DOCKER_TESTS environment variable is set
        if env::var("SKIP_DOCKER_TESTS").is_ok() {
            tracing::info!("Skipping Docker test");
            return;
        }

        // Connect to Docker
        let docker = Docker::connect_with_socket_defaults().unwrap();

        // Create a Manager with a small pool size
        let pool_size = 2;
        let mut manager = Manager {
            docker: docker.clone(),
            runner_image_name: "plgnai/nearai_cvm_runner".to_string(),
            free_cvm_ports: VecDeque::with_capacity(pool_size),
        };

        // Fill the pool
        let result = manager.fill_cvm_pool().await;

        // Verify the result is Ok
        assert!(
            result.is_ok(),
            "Failed to fill CVM pool: {:?}",
            result.err()
        );

        // Verify the pool is filled with the expected number of ports
        assert_eq!(
            manager.free_cvm_ports.len(),
            pool_size,
            "Pool size doesn't match expected size"
        );

        // Verify each port is valid (non-zero)
        for port in &manager.free_cvm_ports {
            assert!(*port > 0, "Invalid port number: {}", port);
        }

        // Clean up the containers after test
        // We need to get the container IDs from the Docker API
        let containers = docker.list_containers::<String>(None).await.unwrap();
        for container in containers {
            if let Some(names) = container.names {
                for name in names {
                    if name.starts_with("/cvm-") {
                        if let Some(id) = container.id.clone() {
                            let _ = docker.stop_container(&id, None).await;
                            let _ = docker.remove_container(&id, None).await;
                            tracing::info!("Cleaned up container: {}", id);
                        }
                    }
                }
            }
        }
    }

    #[tokio::test]
    async fn test_manager_new_fills_pool() {
        // Initialize tracing for tests
        let _ = tracing_subscriber::fmt::try_init();

        // Skip test if SKIP_DOCKER_TESTS environment variable is set
        if env::var("SKIP_DOCKER_TESTS").is_ok() {
            tracing::info!("Skipping Docker test");
            return;
        }

        // Connect to Docker
        let docker = Docker::connect_with_socket_defaults().unwrap();

        // Create a Manager with a small pool size
        let pool_size = 2;
        let manager_result = Manager::new(docker.clone(), pool_size).await;

        // Verify the result is Ok
        assert!(
            manager_result.is_ok(),
            "Failed to create Manager: {:?}",
            manager_result.err()
        );

        let manager = manager_result.unwrap();

        // Verify the pool is filled with the expected number of ports
        assert_eq!(
            manager.free_cvm_ports.len(),
            pool_size,
            "Pool size doesn't match expected size"
        );

        // Verify each port is valid (non-zero)
        for port in &manager.free_cvm_ports {
            assert!(*port > 0, "Invalid port number: {}", port);
        }

        // Clean up the containers after test
        // We need to get the container IDs from the Docker API
        let containers = docker.list_containers::<String>(None).await.unwrap();
        for container in containers {
            if let Some(names) = container.names {
                for name in names {
                    if name.starts_with("/cvm-") {
                        if let Some(id) = container.id.clone() {
                            let _ = docker.stop_container(&id, None).await;
                            let _ = docker.remove_container(&id, None).await;
                            tracing::info!("Cleaned up container: {}", id);
                        }
                    }
                }
            }
        }
    }
}
