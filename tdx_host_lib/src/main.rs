use std::path::Path;
use tempfile::tempdir;

fn main() -> anyhow::Result<()> {
    let manager = tdx_host_lib::DStackManager::new();
    let dir = tempdir().unwrap();

    // Create a Path from the string
    let db_path = Path::new("db.yaml");
    let image_path = Path::new("/home/ubuntu/private-ml-sdk/images/dstack-nvidia-dev-0.3.3");

    // Convert string ports to a Vec<String>
    let ports: Vec<String> = vec![
        "tcp:0.0.0.0:3307:8000".to_string(), // quote on port 8000
        "tcp:0.0.0.0:3306:3306".to_string(),
        "tcp:8080:8080".to_string(),
        "tcp:9000:9000".to_string(),
    ];

    // Empty vector for GPUs
    let gpus: Vec<String> = Vec::new();

    manager.setup_instance(
        db_path,
        Some(dir.path().to_path_buf()),
        image_path,
        12,
        "32G",
        "500G",
        &gpus,
        &ports,
        true,
    )?;

    manager.add_shared_file(dir.path(), "db.yaml")?;

    Ok(())
}
