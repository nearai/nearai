use anyhow::{anyhow, Context, Result};
use ini::configparser::ini::Ini;
use log::{info, warn};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::fs::{self, File};
use std::io::{BufReader, BufWriter, Read};
use std::num::ParseIntError;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};
use tracing;
use uuid::Uuid;

/// Merge two JSON values in a nested/dict-like way, similar to Python's merge2.
fn merge2(a: &Value, b: &Value) -> Value {
    match (a, b) {
        (Value::Object(a_map), Value::Object(b_map)) => {
            let mut c = a_map.clone();
            for (k, v) in b_map.iter() {
                let merged_value = merge2(c.get(k).unwrap_or(&Value::Null), v);
                c.insert(k.clone(), merged_value);
            }
            Value::Object(c)
        }
        (_, Value::Null) => a.clone(),
        _ => b.clone(),
    }
}

/// Load an INI file into a JSON object (section -> { key -> value }).
fn ini_to_value(path: &Path) -> Result<Value> {
    let mut ini = Ini::new();
    let path_str = path.to_str().context("Path is not valid UTF-8")?;
    ini.load(path_str)
        .map_err(|e| anyhow!(e))
        .context("Failed to load INI file")?;

    let mut root = serde_json::Map::new();
    if let Some(sections) = ini.get_map() {
        for (section, properties) in sections.iter() {
            let mut section_map = serde_json::Map::new();
            for (key, value) in properties.iter() {
                // Properly handle Option<String> by using unwrap_or_default()
                let value_str = match value {
                    Some(v) => v.clone(),
                    None => String::default(),
                };
                section_map.insert(key.to_string(), Value::String(value_str));
            }
            root.insert(section.to_string(), Value::Object(section_map));
        }
    }

    Ok(Value::Object(root))
}

/// Generate all candidate config file paths, e.g. `/etc/dstack/client.conf`,
/// `~/.config/dstack/client.conf`, and so on.
fn generate_config_paths() -> Vec<PathBuf> {
    let mut paths = vec![
        PathBuf::from("/etc/dstack/client.conf"),
        dirs::home_dir()
            .map(|mut p| {
                p.push(".config/dstack/client.conf");
                p
            })
            .unwrap_or_default(),
    ];

    // Also walk up from current directory, appending `.dstack/client.conf`
    let mut current_dir = std::env::current_dir().unwrap();
    while current_dir != PathBuf::from("/") {
        let mut conf_path = current_dir.clone();
        conf_path.push(".dstack");
        conf_path.push("client.conf");
        paths.push(conf_path);
        if !current_dir.pop() {
            break;
        }
    }

    paths
}

/// Load and merge all found configs in the standard path list.
fn load_configs_merged() -> Value {
    let mut merged = Value::Null;
    for path in generate_config_paths() {
        if path.exists() {
            info!("Loading configuration from {}", path.display());
            match ini_to_value(&path) {
                Ok(v) => merged = merge2(&merged, &v),
                Err(e) => warn!("Failed to parse '{}': {}", path.display(), e),
            }
        }
    }
    merged
}

/// The main user-facing config, analogous to the Python `DStackConfig`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DStackConfig {
    pub docker_registry: Option<String>,
    pub default_image_name: String,
    pub qemu_path: String,
}

impl Default for DStackConfig {
    fn default() -> Self {
        Self {
            docker_registry: None,
            default_image_name: "".to_string(),
            qemu_path: "qemu-system-x86_64".to_string(),
        }
    }
}

impl DStackConfig {
    /// Loads and merges configuration from all known config paths.
    pub fn load() -> Self {
        let merged = load_configs_merged();

        fn cfg_get(
            root: &Value,
            section: &str,
            key: &str,
            fallback: Option<String>,
        ) -> Option<String> {
            root.get(section)
                .and_then(|sec_val| {
                    if let Value::Object(obj) = sec_val {
                        obj.get(key).and_then(|v| v.as_str().map(|s| s.to_string()))
                    } else {
                        None
                    }
                })
                .or(fallback)
        }

        let mut me = DStackConfig::default();
        let fallback_reg = me.docker_registry.clone();
        me.docker_registry = cfg_get(&merged, "docker", "registry", fallback_reg);
        me.default_image_name = cfg_get(&merged, "image", "default", Some(me.default_image_name))
            .unwrap_or_else(|| "".to_string());
        me.qemu_path = cfg_get(&merged, "qemu", "path", Some(me.qemu_path))
            .unwrap_or_else(|| "qemu-system-x86_64".to_string());
        me
    }
}

/// PortMap, same as in Python.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortMap {
    pub address: String,
    pub protocol: String,
    #[serde(rename = "from")]
    pub from_port: u16,
    #[serde(rename = "to")]
    pub to_port: u16,
}

/// VMConfig, same as in Python.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VMConfig {
    pub id: String,
    pub name: String,
    pub vcpu: u32,
    pub gpu: Vec<String>,
    pub memory: u64,
    pub disk_size: u64,
    pub image: String,
    pub image_path: String,
    pub port_map: Vec<PortMap>,
    pub created_at_ms: u64,
}

/// Convert a memory string (e.g. "1G", "512M", "2T") to MB.
fn memory_to_mb(mem: &str) -> Result<u64> {
    let upper = mem.trim().to_uppercase();
    if upper.ends_with('T') {
        let val: u64 = upper.trim_end_matches('T').parse()?;
        Ok(val * 1024 * 1024)
    } else if upper.ends_with('G') {
        let val: u64 = upper.trim_end_matches('G').parse()?;
        Ok(val * 1024)
    } else if upper.ends_with('M') {
        let val: u64 = upper.trim_end_matches('M').parse()?;
        Ok(val)
    } else {
        // treat as MB directly
        Ok(upper.parse()?)
    }
}

/// Parse a port mapping string "protocol[:address]:from:to".
fn parse_port_mapping(port_str: &str) -> Result<PortMap> {
    let parts: Vec<_> = port_str.split(':').collect();
    match parts.len() {
        // e.g. tcp:8080:80 => proto=tcp, address=127.0.0.1, from=8080, to=80
        3 => {
            let proto = parts[0].to_lowercase();
            let from_port = parts[1]
                .parse::<u16>()
                .map_err(|e: ParseIntError| anyhow!("Invalid from-port: {}", e))?;
            let to_port = parts[2]
                .parse::<u16>()
                .map_err(|e: ParseIntError| anyhow!("Invalid to-port: {}", e))?;
            Ok(PortMap {
                address: "127.0.0.1".to_string(),
                protocol: proto,
                from_port,
                to_port,
            })
        }
        // e.g. tcp:0.0.0.0:8080:80 => proto=tcp, address=0.0.0.0, from=8080, to=80
        4 => {
            let proto = parts[0].to_lowercase();
            let address = parts[1].to_string();
            let from_port = parts[2]
                .parse::<u16>()
                .map_err(|e: ParseIntError| anyhow!("Invalid from-port: {}", e))?;
            let to_port = parts[3]
                .parse::<u16>()
                .map_err(|e: ParseIntError| anyhow!("Invalid to-port: {}", e))?;
            Ok(PortMap {
                address,
                protocol: proto,
                from_port,
                to_port,
            })
        }
        _ => Err(anyhow!(
            "Invalid port mapping format. Use 'protocol[:address]:from:to' for '{}'",
            port_str
        )),
    }
}

/// The main struct replicating the Python `DStackManager`.
pub struct DStackManager {
    run_path: PathBuf,
    pub config: DStackConfig,
    qemu_processes: Arc<Mutex<Vec<std::process::Child>>>,
}

impl DStackManager {
    /// Create a new manager, loading DStackConfig and setting up the default run_path.
    pub fn new() -> Self {
        let run_path = std::env::var("RUN_PATH")
            .map(PathBuf::from)
            .unwrap_or_else(|_| PathBuf::from("./vms"));
        // Attempt to canonicalize so we have an absolute path
        let run_path = run_path.canonicalize().unwrap_or_else(|_| run_path.clone());
        let config = DStackConfig::load();

        DStackManager {
            run_path,
            config,
            qemu_processes: Arc::new(Mutex::new(Vec::new())),
        }
    }

    fn generate_instance_id(&self) -> String {
        Uuid::new_v4().to_string()
    }

    /// Create necessary directories for a new instance, failing if they exist.
    fn create_directories(&self, work_dir: &Path) -> Result<(PathBuf, PathBuf)> {
        // Check if work_dir exists and is empty
        if work_dir.exists() {
            let entries = fs::read_dir(work_dir)?;
            if entries.count() > 0 {
                return Err(anyhow!(
                    "Work directory {} is not empty",
                    work_dir.display()
                ));
            }
        }

        let shared_dir = work_dir.join("shared");
        let certs_dir = shared_dir.join("certs");
        fs::create_dir_all(&shared_dir)?;
        fs::create_dir_all(&certs_dir)?;
        Ok((shared_dir, certs_dir))
    }

    fn read_compose_file(&self, compose_file: &Path) -> Result<String> {
        if !compose_file.is_file() {
            return Err(anyhow!(
                "Compose file not found: {}",
                compose_file.display()
            ));
        }
        let mut f = File::open(compose_file)?;
        let mut content = String::new();
        f.read_to_string(&mut content)?;
        Ok(content)
    }

    fn read_image_metadata(&self, image_path: &Path) -> Result<String> {
        let metadata_path = image_path.join("metadata.json");
        if !metadata_path.is_file() {
            return Err(anyhow!(
                "Image metadata not found at {}",
                metadata_path.display()
            ));
        }
        let file = File::open(&metadata_path)?;
        let meta: Value = serde_json::from_reader(file).with_context(|| {
            format!("Invalid JSON in metadata file {}", metadata_path.display())
        })?;
        let rootfs_hash = meta
            .get("rootfs_hash")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("rootfs_hash not found in image info"))?;
        Ok(rootfs_hash.to_string())
    }

    /// Equivalent to `setup_instance` in Python. Creates the instance directories,
    /// writes out `app-compose.json`, `config.json`, and `vm-manifest.json`.
    ///
    /// - `compose_file`: path to docker-compose.yml (or similar).
    /// - `work_dir_arg`: optional instance directory override. If `None`, we generate a random ID.
    /// - `image_path`: path to the VM image directory (containing `metadata.json`).
    /// - `vcpus`, `memory_str`, `disk_str`: resource specs.
    /// - `gpus`: a list of GPU device IDs to pass through.
    /// - `ports`: a list of port mappings in `protocol[:address]:from:to` format.
    /// - `local_key_provider`: whether to enable local key provider
    pub fn setup_instance(
        &self,
        compose_file: &Path,
        work_dir_arg: Option<PathBuf>,
        image_path: &Path,
        vcpus: u32,
        memory_str: &str,
        disk_str: &str,
        gpus: &[String],
        ports: &[String],
        local_key_provider: bool,
    ) -> Result<()> {
        // Determine the instance ID
        let instance_id = match &work_dir_arg {
            Some(dir) => dir
                .file_name()
                .unwrap_or_else(|| std::ffi::OsStr::new("unnamed"))
                .to_string_lossy()
                .to_string(),
            None => self.generate_instance_id(),
        };
        let work_dir = work_dir_arg.unwrap_or_else(|| self.run_path.join(&instance_id));

        // 1) Create directories
        let (shared_dir, _certs_dir) = self.create_directories(&work_dir)?;

        // 2) Read compose file
        let compose_content = self.read_compose_file(compose_file)?;

        // 3) Write app-compose.json
        let app_compose = json!({
            "manifest_version": 1,
            "name": "example",
            "version": "1.0.0",
            "features": [],
            "runner": "docker-compose",
            "docker_compose_file": compose_content,
            "local_key_provider_enabled": local_key_provider,
        });
        {
            let path = shared_dir.join("app-compose.json");
            let mut f = BufWriter::new(File::create(path)?);
            serde_json::to_writer_pretty(&mut f, &app_compose)?;
        }

        // 4) Read image metadata
        let rootfs_hash = self.read_image_metadata(image_path)?;

        // 5) Write config.json
        let config_obj = json!({
            "rootfs_hash": rootfs_hash,
            "docker_registry": self.config.docker_registry,
            "pccs_url": "https://api.trustedservices.intel.com/sgx/certification/v4",
        });
        {
            let path = shared_dir.join("config.json");
            let mut cf = BufWriter::new(File::create(path)?);
            serde_json::to_writer_pretty(&mut cf, &config_obj)?;
        }

        // 6) Create VM manifest
        let memory_mb = memory_to_mb(memory_str)?;
        let disk_mb = memory_to_mb(disk_str)? / 1024; // Python divides by 1024 => "GB"
        let mut port_map_vec = Vec::new();
        for p in ports {
            port_map_vec.push(parse_port_mapping(p)?);
        }

        let created_at_ms = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64;

        let image_name = image_path
            .file_name()
            .unwrap_or_else(|| std::ffi::OsStr::new("unknown"))
            .to_string_lossy()
            .to_string();

        let vm_config = VMConfig {
            id: instance_id.clone(),
            name: "example".to_string(),
            vcpu: vcpus,
            gpu: gpus.to_vec(),
            memory: memory_mb,
            disk_size: disk_mb,
            image_path: image_path.display().to_string(),
            image: image_name,
            port_map: port_map_vec,
            created_at_ms,
        };

        {
            let path = work_dir.join("vm-manifest.json");
            let mut mf = BufWriter::new(File::create(path)?);
            serde_json::to_writer_pretty(&mut mf, &vm_config)?;
        }

        info!(
            "Work directory prepared successfully at: {}",
            work_dir.display()
        );
        Ok(())
    }

    /// Check if QEMU is installed and available
    fn check_qemu_available(&self) -> Result<()> {
        tracing::info!(
            "Checking if QEMU is available at: {}",
            self.config.qemu_path
        );

        let output = Command::new(&self.config.qemu_path)
            .arg("--version")
            .output()
            .with_context(|| format!("Failed to execute QEMU at: {}", self.config.qemu_path))?;

        if output.status.success() {
            let version = String::from_utf8_lossy(&output.stdout);
            tracing::info!("QEMU version: {}", version.trim());
            Ok(())
        } else {
            let error = String::from_utf8_lossy(&output.stderr);
            tracing::error!("QEMU check failed: {}", error);
            Err(anyhow!("QEMU check failed: {}", error))
        }
    }

    /// Equivalent to `run_instance` in Python. Spawns a QEMU process with TDX options.
    ///
    /// - `vm_dir`: The directory containing `vm-manifest.json` and `shared/`.
    /// - `host_port`: The host key provider port. We'll patch `config.json` to point to this.
    /// - `memory`: Optional memory specification (e.g. "1G", "512M").
    /// - `vcpus`: Optional number of vCPUs.
    /// - `imgdir`: Optional path to the image directory if not specified in manifest.
    /// - `pin_numa`: Whether to pin the VM to the NUMA node of the GPU.
    /// - `hugepage`: Whether to use hugepages for memory.
    pub fn run_instance(
        &self,
        vm_dir: &Path,
        host_port: u16,
        memory: Option<&str>,
        vcpus: Option<u32>,
        imgdir: Option<&Path>,
        pin_numa: bool,
        hugepage: bool,
    ) -> Result<()> {
        // Check if QEMU is available
        self.check_qemu_available()?;

        // 1) Load vm-manifest.json
        let manifest_path = vm_dir.join("vm-manifest.json");
        if !manifest_path.exists() {
            return Err(anyhow!(
                "VM manifest not found in {}",
                manifest_path.display()
            ));
        }
        let mf = BufReader::new(File::open(&manifest_path)?);
        let vm_config: VMConfig = serde_json::from_reader(mf)
            .with_context(|| format!("Failed to parse {}", manifest_path.display()))?;

        // 2) Resolve the image path
        let image_path = if vm_config.image_path.is_empty() {
            if let Some(idir) = imgdir {
                idir.join(&vm_config.image)
            } else {
                return Err(anyhow!(
                    "No image path in manifest and no `imgdir` provided"
                ));
            }
        } else {
            PathBuf::from(&vm_config.image_path)
        };
        let img_metadata_path = image_path.join("metadata.json");
        if !img_metadata_path.exists() {
            return Err(anyhow!(
                "Image metadata not found: {}",
                img_metadata_path.display()
            ));
        }

        // 3) Patch config.json with new host_api_url, host_vsock_port
        let shared_dir = vm_dir.join("shared");
        let config_file = shared_dir.join("config.json");
        if config_file.exists() {
            let mut existing: Value = {
                let cf = BufReader::new(File::open(&config_file)?);
                serde_json::from_reader(cf)?
            };
            if let Value::Object(ref mut map) = existing {
                // e.g. "host_api_url": "http://10.0.2.2:host_port/api"
                map.insert(
                    "host_api_url".to_string(),
                    Value::String(format!("http://10.0.2.2:{}/api", host_port)),
                );
                map.insert(
                    "host_vsock_port".to_string(),
                    Value::Number(host_port.into()),
                );
            }
            let mut wf = BufWriter::new(File::create(&config_file)?);
            serde_json::to_writer_pretty(&mut wf, &existing)?;
        }

        // 4) Read image metadata
        let img_meta_f = BufReader::new(File::open(&img_metadata_path)?);
        let img_metadata: Value = serde_json::from_reader(img_meta_f)
            .with_context(|| format!("Invalid JSON in {}", img_metadata_path.display()))?;

        // Extract needed fields
        let kernel = img_metadata
            .get("kernel")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("Missing 'kernel' in metadata"))?;
        let initrd = img_metadata
            .get("initrd")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("Missing 'initrd' in metadata"))?;
        let bios = img_metadata
            .get("bios")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("Missing 'bios' in metadata"))?;
        let rootfs = img_metadata
            .get("rootfs")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("Missing 'rootfs' in metadata"))?;
        let cmdline = img_metadata
            .get("cmdline")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("Missing 'cmdline' in metadata"))?;

        // 5) Build QEMU command
        let mem_mb = if let Some(m_str) = memory {
            memory_to_mb(m_str)?
        } else {
            vm_config.memory
        };
        let vcpus = vcpus.unwrap_or(vm_config.vcpu);
        let disk_size = vm_config.disk_size;
        let gpus = &vm_config.gpu;

        // create disk if needed
        let vda = vm_dir.join("hda.img");
        if !vda.exists() {
            let disk_arg = format!("{}G", disk_size);
            Command::new("qemu-img")
                .args(&["create", "-f", "qcow2"])
                .arg(&vda)
                .arg(&disk_arg)
                .status()
                .with_context(|| format!("Failed to create disk image at {}", vda.display()))?
                .success()
                .then_some(())
                .ok_or_else(|| anyhow!("qemu-img create command failed"))?;
        }

        // random vsock CID in [3..10003)
        let cid: u16 = (rand::random::<u16>() % 10000) + 3;

        // Base QEMU args
        let mut cmd = vec![
            self.config.qemu_path.clone(),
            "-accel".to_string(),
            "kvm".to_string(),
            "-m".to_string(),
            format!("{}M", mem_mb),
            "-smp".to_string(),
            format!("{}", vcpus),
            "-cpu".to_string(),
            "host".to_string(),
            "-machine".to_string(),
            "q35,kernel_irqchip=split,confidential-guest-support=tdx,hpet=off".to_string(),
            "-object".to_string(),
            "tdx-guest,id=tdx".to_string(),
            "-nographic".to_string(),
            "-nodefaults".to_string(),
            "-chardev".to_string(),
            "null,id=ser0".to_string(),
            "-serial".to_string(),
            "chardev:ser0".to_string(),
            "-kernel".to_string(),
            image_path.join(kernel).display().to_string(),
            "-initrd".to_string(),
            image_path.join(initrd).display().to_string(),
            "-bios".to_string(),
            image_path.join(bios).display().to_string(),
            "-cdrom".to_string(),
            image_path.join(rootfs).display().to_string(),
            "-drive".to_string(),
            format!("file={},if=none,id=virtio-disk0", vda.display()),
            "-device".to_string(),
            "virtio-blk-pci,drive=virtio-disk0".to_string(),
            "-virtfs".to_string(),
            format!(
                "local,path={},mount_tag=host-shared,readonly=off,security_model=mapped,id=virtfs0",
                shared_dir.display()
            ),
            "-device".to_string(),
            format!("vhost-vsock-pci,guest-cid={}", cid),
        ];

        // user networking with port forward
        // e.g.: -device virtio-net-pci,netdev=nic0_td
        //       -netdev user,id=nic0_td,hostfwd=tcp:127.0.0.1:8080-:80, ...
        let mut port_forwards = Vec::new();
        for pm in &vm_config.port_map {
            port_forwards.push(format!(
                "hostfwd={}:{}:{}-:{}",
                pm.protocol, pm.address, pm.from_port, pm.to_port
            ));
        }
        let mut netdev = String::from("user,id=nic0_td");
        for pf in &port_forwards {
            netdev.push(',');
            netdev.push_str(pf);
        }
        cmd.push("-device".to_string());
        cmd.push("virtio-net-pci,netdev=nic0_td".to_string());
        cmd.push("-netdev".to_string());
        cmd.push(netdev);

        // If we have any GPUs, we replicate the Python logic to:
        // 1) prepend "sudo"
        // 2) add extra devices
        let mut final_cmd = Vec::new();
        if !gpus.is_empty() {
            final_cmd.push("sudo".to_string());
        }
        final_cmd.extend(cmd);

        if !gpus.is_empty() {
            final_cmd.push("-device".to_string());
            final_cmd.push("pcie-root-port,id=pci.1,bus=pcie.0".to_string());
            final_cmd.push("-fw_cfg".to_string());
            final_cmd.push("name=opt/ovmf/X-PciMmio64,string=262144".to_string());
            for (i, gpu_id) in gpus.iter().enumerate() {
                final_cmd.push("-object".to_string());
                final_cmd.push(format!("iommufd,id=iommufd{}", i));
                final_cmd.push("-device".to_string());
                final_cmd.push(format!(
                    "vfio-pci,host={},bus=pci.1,iommufd=iommufd{}",
                    gpu_id, i
                ));
            }
        }

        // Append cmdline
        final_cmd.push("-append".to_string());
        final_cmd.push(cmdline.to_string());

        // If pin_numa and exactly one GPU, do the same sysfs-based approach as Python
        if pin_numa && gpus.len() == 1 {
            let sys_path = format!("/sys/bus/pci/devices/0000:{}/numa_node", gpus[0]);
            let numa_node = fs::read_to_string(&sys_path)
                .with_context(|| format!("Failed to read NUMA node from {}", sys_path))?
                .trim()
                .to_string();

            let cpu_list_path = format!("/sys/devices/system/node/node{}/cpulist", numa_node);
            let cpus_list = fs::read_to_string(&cpu_list_path)
                .with_context(|| format!("Failed to read CPU list from {}", cpu_list_path))?
                .trim()
                .to_string();

            // Prepend "taskset -c <cpus_list>" to final_cmd
            let mut pinned = vec!["taskset".to_string(), "-c".to_string(), cpus_list.clone()];
            pinned.append(&mut final_cmd);
            final_cmd = pinned;

            if hugepage {
                // We also add:
                //   -numa node,nodeid=0,cpus=0-(vcpus-1),memdev=mem0
                //   -object memory-backend-file,id=mem0,size={mem_mb}M,mem-path=/dev/hugepages,share=on,prealloc=yes,host-nodes={numa_node},policy=bind
                let huge_obj = format!(
                    "memory-backend-file,id=mem0,size={}M,mem-path=/dev/hugepages,share=on,prealloc=yes,host-nodes={},policy=bind",
                    mem_mb, numa_node
                );
                final_cmd.push("-numa".to_string());
                final_cmd.push(format!("node,nodeid=0,cpus=0-{},memdev=mem0", vcpus - 1));
                final_cmd.push("-object".to_string());
                final_cmd.push(huge_obj);
            }
        }

        // Print for debugging
        println!("Launching QEMU with command:\n{}", final_cmd.join(" "));
        tracing::info!("Launching QEMU with command:\n{}", final_cmd.join(" "));

        // Check if the image files exist
        tracing::info!(
            "Checking if kernel exists: {}",
            image_path.join(kernel).display()
        );
        if !image_path.join(kernel).exists() {
            tracing::error!(
                "Kernel file not found: {}",
                image_path.join(kernel).display()
            );
            return Err(anyhow!(
                "Kernel file not found: {}",
                image_path.join(kernel).display()
            ));
        }

        tracing::info!(
            "Checking if initrd exists: {}",
            image_path.join(initrd).display()
        );
        if !image_path.join(initrd).exists() {
            tracing::error!(
                "Initrd file not found: {}",
                image_path.join(initrd).display()
            );
            return Err(anyhow!(
                "Initrd file not found: {}",
                image_path.join(initrd).display()
            ));
        }

        tracing::info!(
            "Checking if bios exists: {}",
            image_path.join(bios).display()
        );
        if !image_path.join(bios).exists() {
            tracing::error!("BIOS file not found: {}", image_path.join(bios).display());
            return Err(anyhow!(
                "BIOS file not found: {}",
                image_path.join(bios).display()
            ));
        }

        tracing::info!(
            "Checking if rootfs exists: {}",
            image_path.join(rootfs).display()
        );
        if !image_path.join(rootfs).exists() {
            tracing::error!(
                "Rootfs file not found: {}",
                image_path.join(rootfs).display()
            );
            return Err(anyhow!(
                "Rootfs file not found: {}",
                image_path.join(rootfs).display()
            ));
        }

        // Create log files for QEMU output
        let stdout_log = PathBuf::from("qemu_stdout.log");
        let stderr_log = PathBuf::from("qemu_stderr.log");

        tracing::info!("QEMU stdout will be logged to: {}", stdout_log.display());
        tracing::info!("QEMU stderr will be logged to: {}", stderr_log.display());

        let stdout_file = File::create(&stdout_log).with_context(|| {
            format!("Failed to create stdout log file: {}", stdout_log.display())
        })?;
        let stderr_file = File::create(&stderr_log).with_context(|| {
            format!("Failed to create stderr log file: {}", stderr_log.display())
        })?;

        // 6) spawn QEMU
        let child = Command::new(&final_cmd[0])
            .args(&final_cmd[1..])
            .stdin(Stdio::null())
            .stdout(Stdio::from(stdout_file))
            .stderr(Stdio::from(stderr_file))
            .spawn()
            .with_context(|| format!("Failed to launch QEMU: {:?}", final_cmd))?;

        tracing::info!("QEMU process started with PID: {}", child.id());

        {
            let mut procs = self.qemu_processes.lock().unwrap();
            procs.push(child);
        }
        Ok(())
    }

    /// Similar to the Python's `shutdown_instances`.
    /// Terminates each child QEMU process we have started.
    pub fn shutdown_instances(&self) -> Result<()> {
        let mut procs = self.qemu_processes.lock().unwrap();
        tracing::info!("Shutting down {} QEMU instances", procs.len());

        for child in procs.iter_mut() {
            let pid = child.id();
            tracing::info!("Shutting down QEMU instance (pid {})...", pid);

            match child.kill() {
                Ok(_) => tracing::info!("Sent kill signal to QEMU process {}", pid),
                Err(e) => {
                    tracing::warn!("Failed to send kill signal to QEMU process {}: {}", pid, e)
                }
            }

            match child.wait() {
                Ok(status) => {
                    tracing::info!("QEMU process {} exited with status: {:?}", pid, status)
                }
                Err(e) => tracing::error!("Error waiting for QEMU process {}: {:?}", pid, e),
            }
        }

        let count = procs.len();
        procs.clear();
        tracing::info!("Cleared {} QEMU processes from tracking list", count);

        Ok(())
    }

    /// Equivalent to the Python's `list_available_gpus()`.
    /// Uses `lspci` to scan for lines containing "NVIDIA".
    pub fn list_available_gpus(&self) -> Result<Vec<String>> {
        let output = Command::new("lspci")
            .stdout(Stdio::piped())
            .spawn()?
            .wait_with_output()?;
        let stdout = String::from_utf8_lossy(&output.stdout);
        let lines: Vec<String> = stdout
            .lines()
            .filter(|line| line.contains("NVIDIA"))
            .map(|s| s.to_string())
            .collect();
        Ok(lines)
    }

    /// Copy a file to the VM's shared directory.
    ///
    /// - `vm_dir`: The directory containing the VM instance.
    /// - `file_path`: The path to the file to copy, relative to the crate's directory.
    pub fn add_shared_file(&self, vm_dir: &Path, file_path: &str) -> Result<()> {
        let src_path = Path::new(file_path);
        // Get the destination path in the VM's shared directory
        let dest_path = vm_dir.join("shared").join(file_path);

        // Create parent directories if they don't exist
        if let Some(parent) = dest_path.parent() {
            fs::create_dir_all(parent)?;
        }

        // Copy the file, preserving metadata
        fs::copy(&src_path, &dest_path).with_context(|| {
            format!(
                "Failed to copy {} to {}",
                src_path.display(),
                dest_path.display()
            )
        })?;

        Ok(())
    }
}

// (Optional) You could add unit tests for your merge2 or memory_to_mb, etc.
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_merge2() {
        let a = json!({"a":1});
        let b = json!({"b":2});
        let merged = merge2(&a, &b);
        assert_eq!(merged, json!({"a":1,"b":2}));

        let a = json!({"a":{"b":1}});
        let b = json!({"a":{"c":2}});
        let merged = merge2(&a, &b);
        assert_eq!(merged, json!({"a":{"b":1,"c":2}}));
    }

    #[test]
    fn test_memory_to_mb() {
        assert_eq!(memory_to_mb("512").unwrap(), 512);
        assert_eq!(memory_to_mb("1G").unwrap(), 1024);
        assert_eq!(memory_to_mb("2G").unwrap(), 2048);
        assert_eq!(memory_to_mb("2T").unwrap(), 2 * 1024 * 1024);
    }

    #[test]
    fn test_parse_port_mapping() {
        // Valid mappings
        let pm1 = parse_port_mapping("tcp:8080:80").unwrap();
        assert_eq!(pm1.protocol, "tcp");
        assert_eq!(pm1.address, "127.0.0.1");
        assert_eq!(pm1.from_port, 8080);
        assert_eq!(pm1.to_port, 80);

        let pm2 = parse_port_mapping("udp:0.0.0.0:53:53").unwrap();
        assert_eq!(pm2.protocol, "udp");
        assert_eq!(pm2.address, "0.0.0.0");
        assert_eq!(pm2.from_port, 53);
        assert_eq!(pm2.to_port, 53);

        // Invalid mappings
        assert!(parse_port_mapping("tcp:8080").is_err());
        assert!(parse_port_mapping("notvalid").is_err());
    }

    #[test]
    fn test_ini_to_value() {
        use std::io::Write;
        use tempfile::NamedTempFile;

        // Create a temporary INI file
        let mut temp_ini = NamedTempFile::new().expect("Failed to create temp file");
        writeln!(
            temp_ini,
            "[docker]\nregistry=http://example.com\n\n[qemu]\npath=qemu-system-x86_64"
        )
        .unwrap();

        let path = temp_ini.path();
        let val = ini_to_value(path).expect("Failed to parse INI file");
        assert_eq!(
            val.get("docker")
                .and_then(|section| section.get("registry"))
                .and_then(|v| v.as_str()),
            Some("http://example.com")
        );
        assert_eq!(
            val.get("qemu")
                .and_then(|section| section.get("path"))
                .and_then(|v| v.as_str()),
            Some("qemu-system-x86_64")
        );
    }
}
