use anyhow::{Context, Result};
use base64::Engine;
use dcap_qvl::collateral::get_collateral;
use dcap_qvl::verify::verify;
use reqwest::{Client, header};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha512};
use std::collections::HashMap;
use std::pin::Pin;
use std::process::Command;
use std::time::Duration;
use tempfile::NamedTempFile;
use url::Url;

/// Auth data for CVM client
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthData {
    pub token: String,
    // Add other auth fields as needed
}

/// Request to assign an agent to a CVM
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssignRequest {
    pub agent_id: String,
    pub thread_id: String,
    pub api_url: String,
    pub provider: String,
    pub model: String,
    pub temperature: f32,
    pub max_tokens: u32,
    pub max_iterations: u32,
    pub env_vars: HashMap<String, String>,
}

/// Response for checking if an agent is assigned
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IsAssignedResp {
    pub is_assigned: bool,
    pub agent_id: Option<String>,
}

/// Request to run an agent on a CVM
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunRequest {
    pub run_id: String,
}

/// Response containing a quote
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteResponse {
    pub quote: String,
}

/// TDX Quote Response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TdxQuoteResponse {
    pub quote: String,
}

/// Verification result from TDX quote verification
#[derive(Debug, Serialize, Deserialize)]
pub struct VerificationResult {
    pub report: Report,
    // Add other fields as needed
}

/// Report data from TDX quote verification
#[derive(Debug, Serialize, Deserialize)]
pub struct Report {
    #[serde(rename = "TD10")]
    pub td10: TD10Report,
    // Add other fields as needed
}

/// TD10 report data
#[derive(Debug, Serialize, Deserialize)]
pub struct TD10Report {
    pub report_data: String,
    // Add other fields as needed
}

/// Client for interacting with the CVM service
pub struct CvmClient {
    url: String,
    headers: header::HeaderMap,
    is_attested: bool,
    cert_path: String,
    client: Client,
}

impl CvmClient {
    /// Create a new CVM client
    pub fn new(url: &str, auth: Option<AuthData>) -> Result<Self> {
        // Parse URL to extract hostname and port
        let parsed_url = Url::parse(url).context("Failed to parse URL")?;
        let hostname = parsed_url.host_str().unwrap_or("localhost").to_string();
        let port = parsed_url
            .port()
            .unwrap_or(if parsed_url.scheme() == "https" {
                443
            } else {
                80
            })
            .to_string();

        // Create headers with auth if provided
        let mut headers = header::HeaderMap::new();
        if let Some(auth_data) = auth {
            let auth_json =
                serde_json::to_string(&auth_data).context("Failed to serialize auth data")?;
            let auth_header = format!("Bearer {}", auth_json);
            headers.insert(
                header::AUTHORIZATION,
                header::HeaderValue::from_str(&auth_header)
                    .context("Failed to create auth header")?,
            );
        }

        // Create temporary file for certificate
        let cert_file = NamedTempFile::new().context("Failed to create temp file")?;
        let cert_path = cert_file.path().to_string_lossy().to_string();

        // Keep the file handle alive by not dropping it
        std::mem::forget(cert_file);

        // Fetch server certificate
        let cmd = format!(
            "echo | openssl s_client -connect {}:{} -servername {} -showcerts 2>/dev/null </dev/null | openssl x509 -outform PEM > {}",
            hostname, port, hostname, cert_path
        );

        let status = Command::new("sh")
            .arg("-c")
            .arg(&cmd)
            .status()
            .context("Failed to execute openssl command")?;

        if !status.success() {
            return Err(anyhow::anyhow!("Failed to fetch server certificate"));
        }

        tracing::info!("Certificate saved to {}", cert_path);

        // Create HTTP client
        let client = Client::builder()
            .danger_accept_invalid_certs(true) // We'll handle verification ourselves
            .build()
            .context("Failed to build HTTP client")?;

        Ok(Self {
            url: url.to_string(),
            headers,
            is_attested: false,
            cert_path,
            client,
        })
    }

    /// Make an HTTP request with proper certificate verification
    async fn make_request(
        &mut self,
        method: &str,
        path: &str,
        body: Option<String>,
    ) -> Result<String> {
        // Perform attestation if needed
        if !self.is_attested && path != "quote" {
            tracing::info!("Server not attested yet, performing attestation...");
            // Use Box::pin to avoid infinite recursion in async fn
            let attest_future = self.attest();
            Pin::from(Box::new(attest_future)).await?;
        }

        let url = format!("{}/{}", self.url, path.trim_start_matches('/'));

        let request_builder = match method.to_uppercase().as_str() {
            "GET" => self.client.get(&url),
            "POST" => {
                let mut builder = self.client.post(&url);
                if let Some(json_body) = body {
                    builder = builder
                        .header(header::CONTENT_TYPE, "application/json")
                        .body(json_body);
                }
                builder
            }
            _ => return Err(anyhow::anyhow!("Unsupported HTTP method: {}", method)),
        };

        // Add headers
        let request = request_builder
            .headers(self.headers.clone())
            .build()
            .context("Failed to build request")?;

        // Send request
        let response = self
            .client
            .execute(request)
            .await
            .context("Failed to execute request")?;

        // Check status
        let status = response.status();
        if !status.is_success() {
            let error_text = response.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!(
                "Request failed with status {}: {}",
                status,
                error_text
            ));
        }

        // Return response body
        let body = response
            .text()
            .await
            .context("Failed to read response body")?;
        Ok(body)
    }

    /// Perform attestation
    pub async fn attest(&mut self) -> Result<QuoteResponse> {
        if self.is_attested {
            tracing::info!("Already attested");
            return self.get_quote().await;
        }

        // Get quote from server
        let quote_response = self.get_quote().await?;

        // Get certificate hash and expected report data
        let expected_report_data = self.get_certificate_hash()?;

        // Verify the quote
        self.verify_quote(&quote_response, &expected_report_data)
            .await?;

        tracing::info!("Attestation successful - certificate is now trusted");
        self.is_attested = true;

        Ok(quote_response)
    }

    /// Get certificate hash and generate expected report data
    pub fn get_certificate_hash(&self) -> Result<[u8; 64]> {
        // Get certificate's public key hash
        let cmd = format!(
            "openssl x509 -in {} -pubkey -noout -outform DER | openssl dgst -sha256",
            self.cert_path
        );

        let output = Command::new("sh")
            .arg("-c")
            .arg(&cmd)
            .output()
            .context("Failed to execute openssl command")?;

        if !output.status.success() {
            return Err(anyhow::anyhow!("Failed to get certificate public key hash"));
        }

        let ssl_pub_key = String::from_utf8_lossy(&output.stdout)
            .split("= ")
            .nth(1)
            .ok_or_else(|| anyhow::anyhow!("Failed to parse public key hash"))?
            .trim()
            .to_string();

        // Generate report data for verification
        let expected_report_data = generate_sha512_hash(&ssl_pub_key, "app-data");

        Ok(expected_report_data)
    }

    /// Verify a quote against expected report data
    pub async fn verify_quote(
        &self,
        quote_response: &QuoteResponse,
        expected_report_data: &[u8; 64],
    ) -> Result<()> {
        // Verify quote using dcap_qvl
        tracing::info!("Verifying quote...");

        // Get the raw quote bytes
        let raw_quote = base64::engine::general_purpose::STANDARD
            .decode(&quote_response.quote)
            .context("Failed to decode quote from base64")?;

        // Get the current time in seconds since the Unix epoch
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .context("Failed to get current time")?
            .as_secs();

        // Get collateral from Intel PCCS
        tracing::info!("Fetching quote collateral from Intel PCCS...");
        let pccs_url = "https://pccs.service.intel.com/sgx/certification/v4/";
        let timeout = Duration::from_secs(30);
        let collateral = get_collateral(pccs_url, &raw_quote, timeout)
            .await
            .map_err(|e| anyhow::anyhow!("Failed to get quote collateral: {:?}", e))?;

        // Verify the quote with collateral
        tracing::info!("Verifying quote with collateral...");
        let verified_report = verify(&raw_quote, &collateral, now)
            .map_err(|e| anyhow::anyhow!("Quote verification failed: {:?}", e))?;

        // Log the verification result
        tracing::info!("Quote verified successfully: {:?}", verified_report);

        // Extract and verify the report data
        let report_data = verified_report
            .report
            .as_td10()
            .ok_or_else(|| anyhow::anyhow!("Report data mismatch"))?
            .report_data;

        if report_data != *expected_report_data {
            return Err(anyhow::anyhow!(
                "Report data mismatch: expected {:?}, got {:?}",
                expected_report_data,
                report_data
            ));
        }

        Ok(())
    }

    /// Get quote from server
    pub async fn get_quote(&mut self) -> Result<QuoteResponse> {
        let response = self.make_request("GET", "quote", None).await?;
        let quote_response: QuoteResponse =
            serde_json::from_str(&response).context("Failed to parse quote response")?;
        Ok(quote_response)
    }

    /// Assign an agent to a CVM
    pub async fn assign(&mut self, request: AssignRequest) -> Result<String> {
        tracing::info!("Assigning agent {} to CVM", request.agent_id);
        let body = serde_json::to_string(&request).context("Failed to serialize assign request")?;
        let response = self.make_request("POST", "assign", Some(body)).await?;
        Ok(response)
    }

    /// Run an agent on a CVM
    pub async fn run(&mut self, request: RunRequest) -> Result<String> {
        tracing::info!("Running agent on CVM, run_id: {}", request.run_id);
        let body = serde_json::to_string(&request).context("Failed to serialize run request")?;
        let response = self.make_request("POST", "run", Some(body)).await?;
        Ok(response)
    }

    /// Check if an agent is assigned to the CVM
    pub async fn is_assigned(&mut self) -> Result<IsAssignedResp> {
        let response = self.make_request("GET", "is_assigned", None).await?;
        let is_assigned: IsAssignedResp =
            serde_json::from_str(&response).context("Failed to parse is_assigned response")?;
        tracing::info!("Health response: {:?}", is_assigned);
        Ok(is_assigned)
    }
}

/// Generate SHA-512 hash of the report data with prefix
pub fn generate_sha512_hash(report_data: &str, prefix: &str) -> [u8; 64] {
    let mut hasher = Sha512::new();
    hasher.update(format!("{}:", prefix));
    hasher.update(report_data.as_bytes());
    let hash = hasher.finalize();

    // Convert to fixed-size array
    let mut result = [0u8; 64];
    result.copy_from_slice(&hash);
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::File;
    use std::io::Write;
    use std::path::PathBuf;

    #[test]
    fn test_generate_sha512_hash() {
        let report_data = "test data";
        let prefix = "prefix";
        let hash = generate_sha512_hash(report_data, prefix);
        assert_eq!(hash.len(), 64);
    }

    #[test]
    fn test_get_certificate_hash() {
        // Create a temporary certificate file
        let cert_path_str = PathBuf::from("/tmp/test_cert.pem")
            .to_string_lossy()
            .to_string();

        // Write a dummy certificate to the file
        let dummy_cert = r#"-----BEGIN CERTIFICATE-----
MIIDazCCAlOgAwIBAgIUJFdU6o9MnCCDdmWAGYR2RMjJfMowDQYJKoZIhvcNAQEL
BQAwRTELMAkGA1UEBhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNVBAoM
GEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDAeFw0yMzA0MTIxMzI2MThaFw0yNDA0
MTExMzI2MThaMEUxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEw
HwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQwggEiMA0GCSqGSIb3DQEB
AQUAA4IBDwAwggEKAoIBAQDCpLmrXQXLAN0zr8VMCvM0ImO2r8Gg3JKLdZDEZVKg
BIjY0mN3HwM0y2QkA6hYZ3QnMa3IqJmYzLtA+jR+GJqRIzYMuLWm9AECJXkRiJ6A
RBSp8h0LRZVMhC0U3pdwqdY/XvQQA3T0IBGD/5tZ+GjZQGYCnHV1iMjgp/nWo+Zv
Qv3CKvYpg4g/V3LZ+UjmDmrVdVrJGfuXNHCKGVJKGGJpne0xtDPfkxiPZXkK9tXx
JZwHSi0Na4JQDwlWLDM0qJv3Ql/kYKX+eLvNvGG8ysK1B5zKKQk9KlZJUTQKIQCw
+MBVbVL9y7EIgCXCiW3/nHh8gEKOL6L0a5zKRAGXAgMBAAGjUzBRMB0GA1UdDgQW
BBQVJqRlzepVh5/1Rt/0bzBXvQKnXDAfBgNVHSMEGDAWgBQVJqRlzepVh5/1Rt/0
bzBXvQKnXDAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQBxC7QK
FBUHxN9+MjdRc5MaJFB+9TUjHRNqItMCXwqRGUuGhkY/UXlFkYr9ij5uTJzDLDHb
eYm5UzVPZsQUVRCFG+lTrLZhwu4YWIjQJsYKNUQXzGGDPvgG1vTFP2OCrYF9JTBX
Hn3M9Xyj/XHnDQMOUj8X9jnLXAUcNVh/vKj0E/QvW7yRBXl5Qk+RpFGrL5iYX5/O
BaXHvdEpRyizMdU7RQIqBbZUzEqDgPnGJjNYXxrElzxHQKcQb5Lh1jWx3fGLmgwW
Cq1LkE+vQGFzk/ZkiP9EvP2FnYMGfZnRJIzGLxm2jRqR9GXB/MJXpRQnQVBDyMJO
UXdRQJsvyCFJzLEA
-----END CERTIFICATE-----"#;

        let mut file = File::create(&cert_path_str).unwrap();
        file.write_all(dummy_cert.as_bytes()).unwrap();

        // Create a client with the certificate
        let client = CvmClient {
            url: "https://example.com".to_string(),
            headers: header::HeaderMap::new(),
            is_attested: false,
            cert_path: cert_path_str.clone(),
            client: Client::new(),
        };

        // Get the certificate hash
        let result = client.get_certificate_hash();

        // Verify the result
        assert!(result.is_ok());
        let hash = result.unwrap();
        assert_eq!(hash.len(), 64);

        // Clean up
        std::fs::remove_file(&cert_path_str).unwrap_or_default();
    }
}
