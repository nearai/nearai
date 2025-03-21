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
    active_containers: HashMap<u16, String>, // Map of port -> container_id
}

impl Manager {
    pub async fn new(docker: Docker, pool_size: usize) -> Result<Self> {
        let runner_image_name = "plgnai/nearai_cvm_runner".to_string(); // TDOO: fix to specific version.

        // Pull the image first
        tracing::info!("Pulling CVM runner image...");
        let image_name = runner_image_name.clone();
        let mut stream = docker.create_image(
            Some(CreateImageOptions {
                from_image: image_name.as_str(),
                tag: "latest",
                ..Default::default()
            }),
            None,
            None,
        );

        while let Some(result) = stream.next().await {
            match result {
                Ok(output) => tracing::debug!("Pull progress: {:?}", output),
                Err(e) => return Err(anyhow::anyhow!("Failed to pull image: {}", e)),
            }
        }
        tracing::info!("CVM runner image pulled successfully");

        let mut manager = Self {
            docker,
            runner_image_name,
            free_cvm_ports: VecDeque::with_capacity(pool_size),
            active_containers: HashMap::new(),
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

                    // If attestation fails, the container might be in a bad state
                    // Try to remove it from active_containers and clean it up later
                    if let Some(container_id) = self.active_containers.get(&port) {
                        tracing::warn!(
                            "Container {} for port {} is in a bad state",
                            container_id,
                            port
                        );
                    }

                    continue;
                }
            }
        }

        // If we found a working CVM, remove it from the pool and refill
        if let Some(port) = port_to_return {
            if let Some(index) = index_to_remove {
                self.free_cvm_ports.remove(index);
                // Note: We keep the container in active_containers so we can clean it up later
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

    async fn add_cvm_to_pool(&mut self) -> Result<u16> {
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
                                    // Store the port mapping and container ID
                                    tracing::info!("CVM is accessible on host port {}", host_port);
                                    self.active_containers
                                        .insert(host_port, container.id.clone());
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

    /// Shutdown the manager and clean up all containers
    pub async fn shutdown(&mut self) -> Result<()> {
        tracing::info!("Shutting down Manager and cleaning up resources...");

        // Collect all container IDs (both free and active)
        let mut container_ids = Vec::new();

        // Add container IDs from active_containers
        for (port, container_id) in self.active_containers.drain() {
            tracing::info!("Preparing to stop container for port {}", port);
            container_ids.push(container_id);
        }

        // Get container IDs for free ports
        let free_ports: Vec<u16> = self.free_cvm_ports.drain(..).collect();
        for port in free_ports {
            if let Some(container_id) = self.active_containers.remove(&port) {
                tracing::info!("Preparing to stop container for free port {}", port);
                container_ids.push(container_id);
            }
        }

        // Stop and remove all containers
        for container_id in container_ids {
            // Set a timeout for stopping containers (10 seconds)
            let stop_options = bollard::container::StopContainerOptions { t: 10 };

            tracing::info!("Stopping container: {}", container_id);
            match self
                .docker
                .stop_container(&container_id, Some(stop_options))
                .await
            {
                Ok(_) => tracing::info!("Successfully stopped container: {}", container_id),
                Err(e) => {
                    tracing::warn!("Failed to stop container {}: {}", container_id, e);
                    // Try to kill the container if stopping fails
                    match self
                        .docker
                        .kill_container::<String>(&container_id, None)
                        .await
                    {
                        Ok(_) => tracing::info!("Successfully killed container: {}", container_id),
                        Err(e) => {
                            tracing::warn!("Failed to kill container {}: {}", container_id, e)
                        }
                    }
                }
            }

            // Set force removal option
            let remove_options = bollard::container::RemoveContainerOptions {
                force: true,
                ..Default::default()
            };

            tracing::info!("Removing container: {}", container_id);
            match self
                .docker
                .remove_container(&container_id, Some(remove_options))
                .await
            {
                Ok(_) => tracing::info!("Successfully removed container: {}", container_id),
                Err(e) => tracing::warn!("Failed to remove container {}: {}", container_id, e),
            }
        }

        // Clear the free CVM ports queue and active containers map
        self.free_cvm_ports.clear();
        self.active_containers.clear();

        tracing::info!("Manager shutdown complete");
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
    use uuid::Uuid;

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
        let container_name = format!("test-container-{}", Uuid::new_v4());

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
            Some(&container_name),
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
        let container_name = format!("test-dind-{}", Uuid::new_v4());

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
            Some(&container_name),
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
        let container_name = format!("test-nginx-{}", Uuid::new_v4());

        // Map port 80 to a random port
        let mut exposed_ports = HashMap::new();
        exposed_ports.insert("80/tcp".to_string(), HashMap::new());

        // Create port bindings for host config
        let mut port_bindings = HashMap::new();
        port_bindings.insert(
            "80/tcp".to_string(),
            Some(vec![PortBinding {
                host_ip: Some("0.0.0.0".to_string()),
                host_port: None,
            }]),
        );

        // Create host config with port bindings
        let host_config = HostConfig {
            port_bindings: Some(port_bindings),
            ..Default::default()
        };

        // Create container config
        let container_config = Config {
            image: Some(image_name.to_string()),
            exposed_ports: Some(exposed_ports),
            host_config: Some(host_config),
            ..Default::default()
        };

        // Create container options
        let container_options = CreateContainerOptions {
            name: container_name,
            ..Default::default()
        };

        let docker = Docker::connect_with_socket_defaults().unwrap();

        // Create and start the container
        let container = docker
            .create_container(Some(container_options), container_config)
            .await
            .unwrap();

        docker
            .start_container::<String>(&container.id, None)
            .await
            .unwrap();

        tracing::info!("Started Nginx container with ID: {}", container.id);

        // Get container information to find the assigned host port
        let container_info = docker.inspect_container(&container.id, None).await.unwrap();

        // Extract the host port that was assigned to container port 80
        let mut host_port = None;
        if let Some(network_settings) = container_info.network_settings {
            if let Some(ports) = network_settings.ports {
                if let Some(bindings) = ports.get("80/tcp") {
                    if let Some(bindings_vec) = bindings {
                        if !bindings_vec.is_empty() {
                            let binding = &bindings_vec[0];
                            if let Some(port_str) = &binding.host_port {
                                host_port = Some(port_str.clone());
                                tracing::info!("Nginx is accessible on port {}", port_str);
                            }
                        }
                    }
                }
            }
        }

        // Assert that a port was assigned
        assert!(host_port.is_some(), "No host port was assigned");
        assert!(
            !host_port.unwrap().is_empty(),
            "Host port should not be empty"
        );

        // Clean up the container after test
        let _ = docker.stop_container(&container.id, None).await;
        let _ = docker.remove_container(&container.id, None).await;
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
            active_containers: HashMap::new(),
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
