// tests/test_setup_instance.rs

use std::fs;
use std::io::Write;
use tdx_host_lib::DStackManager; // adjust your crate name accordingly
use tempfile::{tempdir, NamedTempFile};

#[test]
fn test_setup_instance_integration() {
    let manager = DStackManager::new();

    // 1) Create a temporary directory for our "instance"
    let temp_dir = tempdir().expect("Failed to create temp dir");
    let instance_dir = temp_dir.path().join("my_instance");

    // 2) Create a fake docker-compose file
    let mut compose_file = NamedTempFile::new().expect("Failed to create compose file");
    writeln!(
        compose_file,
        r#"
        version: "3"
        services:
          hello:
            image: hello-world
        "#
    )
    .unwrap();
    let compose_path = compose_file.into_temp_path(); // persist it

    // 3) Create a fake image directory with a metadata.json
    let image_dir = temp_dir.path().join("fake_image");
    fs::create_dir_all(&image_dir).unwrap();
    let metadata_path = image_dir.join("metadata.json");
    fs::write(&metadata_path, r#"{"rootfs_hash":"abcd1234"}"#).unwrap();

    // 4) Call setup_instance
    manager
        .setup_instance(
            &compose_path,
            Some(instance_dir.clone()), // override
            &image_dir,
            2,     // vcpus
            "1G",  // memory
            "10G", // disk
            &[],   // gpus
            &["tcp:8080:80".to_string()],
            true, // local_key_provider
        )
        .expect("setup_instance failed");

    // 5) Assert files exist
    let shared_dir = instance_dir.join("shared");
    assert!(shared_dir.join("app-compose.json").exists());
    assert!(shared_dir.join("config.json").exists());
    assert!(instance_dir.join("vm-manifest.json").exists());

    // Optionally read them back and parse JSON
    let app_compose_data = fs::read_to_string(shared_dir.join("app-compose.json")).unwrap();
    let app_compose_json: serde_json::Value = serde_json::from_str(&app_compose_data).unwrap();
    assert_eq!(app_compose_json["manifest_version"], 1);

    let vm_manifest_data = fs::read_to_string(instance_dir.join("vm-manifest.json")).unwrap();
    let vm_manifest_json: serde_json::Value = serde_json::from_str(&vm_manifest_data).unwrap();
    assert_eq!(vm_manifest_json["vcpu"], 2);
}
