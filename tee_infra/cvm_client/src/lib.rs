use anyhow::{Context, Result};
use base64::Engine;
use dcap_qvl::collateral::get_collateral;
use dcap_qvl::collateral::get_collateral_and_verify;
use dcap_qvl::verify::VerifiedReport;
use dcap_qvl::verify::verify;
use near_auth::AuthData;
use reqwest::{Client, header};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha512};
use std::collections::HashMap;
use std::pin::Pin;
use std::process::Command;
use std::time::Duration;
use tempfile::NamedTempFile;
use url::Url;

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
    pub fn new(url: &str, auth: &AuthData) -> Result<Self> {
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
        let auth_json = serde_json::to_string(auth).context("Failed to serialize auth data")?;
        let auth_header = format!("Bearer {}", auth_json);
        headers.insert(
            header::AUTHORIZATION,
            header::HeaderValue::from_str(&auth_header).context("Failed to create auth header")?,
        );

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
        self.verify_quote_and_report_data(&quote_response, &expected_report_data)
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
    pub async fn verify_quote_and_report_data(
        &self,
        quote_response: &QuoteResponse,
        expected_report_data: &[u8; 64],
    ) -> Result<()> {
        // Extract and verify the report data
        let verified_report = self.verify_quote_from_pccs(quote_response).await?;
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

    pub async fn verify_quote_from_pccs(
        &self,
        quote_response: &QuoteResponse,
    ) -> Result<VerifiedReport> {
        tracing::info!("Verifying quote: {:?}", quote_response.quote);

        let raw_quote =
            hex::decode(&quote_response.quote).context("Failed to decode hex-encoded quote")?;
        tracing::info!("Verifying raw quote: {:?}", raw_quote);

        let verified_report = get_collateral_and_verify(&raw_quote, None)
            .await
            .map_err(|e| anyhow::anyhow!("Failed to get quote collateral: {:?}", e))?;

        // Log the verification result
        tracing::debug!("Quote verified successfully: {:?}", verified_report);

        Ok(verified_report)
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

    #[tokio::test]
    async fn test_verify_quote_from_pccs() {
        let _ = tracing_subscriber::fmt::try_init();

        // Create a test client
        let client = CvmClient {
            url: "https://example.com".to_string(),
            headers: header::HeaderMap::new(),
            is_attested: false,
            cert_path: "/tmp/test_cert.pem".to_string(),
            client: Client::new(),
        };

        // Create the quote response
        let quote_response = QuoteResponse {
            quote: "040002008100000000000000939a7233f79c4ca9940a0db3957f060763f5d35aee0010427e9f9b66728d820200000000060103000000000000000000000000005b38e33a6487958b72c3c12a938eaa5e3fd4510c51aeeab58c7d5ecee41d7c436489d6c8e4f92f160b7cad34207b00c100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000e702060000000000c68518a0ebb42136c12b2275164f8c72f25fa9a34392228687ed6e9caeb9c0f1dbd895e9cf475121c029dc47e70e91fd000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000fd27eb7bd91ae271fbaa0149490db3a36b1ee5dcf6ace40bb8325d85c41923cd808cba77b58ed00da4bcf5868031ac7f4a7db64a609c77e85f603c23e9a9fd03bfd9e6b52ce527f774a598e66d58386026cea79b2aea13b81a0b70cfacdec0ca8a4fe048fea22663152ef128853caa5c033cbe66baf32ba1ff7f6b1afc1624c279f50a4cbc522a735ca6f69551e61ef2b9e3af9fc20b2012c207753832d005e32efc5d323521c3963d6769a41afbc3d9a31dce28d2fd0c65de9e920ecb0bba85982c4cc40376e1c12a117f302edf992d0a8d719b52895f2be9c59b15ff168a1cba4fc56fda151f1e2954f01ee1c6a41d7f58efad18d29a37e993814bb77d863ecc100000bb67f9589cff75d34c1948d1dd9da16fd7e8f99c741ce1558e5d3695132a4d79e9bce4f70c94ccad3246a3936c79a527c9bb176f40f37ef40e29274feac260aaa31313c04151ce33d9ea7ae041f899eb6753ed0390e831aeec6b4fda8c853b8793d4f5616ab4bf2fbeebe525401f8ec180c2ec9615df32df2a864fc1b7daaa990600461000000303191b04ff0006000000000000000000000000000000000000000000000000000000000000000000000000000000001500000000000000e700000000000000e5a3a7b5d830c2953b98534c6c59a3a34fdc34e933f7f5898f0a85cf08846bca0000000000000000000000000000000000000000000000000000000000000000dc9e2a7c6f948f17474e34a7fc43ed030f7c1563f1babddf6340c82e0e54a8c500000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002000600000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000f9c6523313cdf40e5464a7db73fed5d0b2e7ca466ece1516eb381192452c51500000000000000000000000000000000000000000000000000000000000000000488f6451a235059acf3f52d3f743e798c324e0f1758cd460f8be1cec3f71dc6b2b2fd92d1a94188e15b471008de1cbefcfcd7943bf49081590de2880d35fe6ce2000000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f05005e0e00002d2d2d2d2d424547494e2043455254494649434154452d2d2d2d2d0a4d49494538544343424a6167417749424167495564304431306f6c714b5436787674435a597a51364e79762b35365177436759494b6f5a497a6a3045417749770a634445694d434147413155454177775a535735305a577767553064594946424453794251624746305a6d397962534244515445614d42674741315545436777520a535735305a577767513239796347397959585270623234784644415342674e564241634d43314e68626e526849454e7359584a684d51737743515944565151490a44414a445154454c4d416b474131554542684d4356564d774868634e4d6a55774d7a45344d4467304e4451305768634e4d7a49774d7a45344d4467304e4451300a576a42774d534977494159445651514444426c4a626e526c624342545231676755454e4c49454e6c636e52705a6d6c6a5958526c4d526f77474159445651514b0a4442464a626e526c6243424462334a7762334a6864476c76626a45554d424947413155454277774c553246756447456751327868636d4578437a414a42674e560a4241674d416b4e424d517377435159445651514745774a56557a425a4d424d4742797147534d34394167454743437147534d343941774548413049414249376e0a4264536a4e6b4c2f554d43394b49646c4443455243766c7374534d73322f6369315730474c6853543942752b6e5a54464936744b6b4a636c516953514e7a626e0a416b66514254684c434d3641784439307631656a67674d4d4d4949444344416642674e5648534d4547444157674253566231334e765276683655424a796454300a4d383442567776655644427242674e56485238455a4442694d47436758714263686c706f64485277637a6f764c32467761533530636e567a6447566b633256790a646d6c6a5a584d75615735305a577775593239744c334e6e6543396a5a584a3061575a7059324630615739754c3359304c33426a61324e796244396a595431770a624746305a6d397962535a6c626d4e765a476c755a7a316b5a584977485159445652304f424259454648366c467730726655396f6566382b5144774530626f520a347761684d41344741315564447745422f775145417749477744414d42674e5648524d4241663845416a41414d4949434f51594a4b6f5a496876684e415130420a424949434b6a4343416959774867594b4b6f5a496876684e4151304241515151664b4243676a773547586a5050384945725266533744434341574d47436971470a534962345451454e41514977676746544d42414743797147534962345451454e41514942416745444d42414743797147534962345451454e41514943416745440a4d42414743797147534962345451454e41514944416745434d42414743797147534962345451454e41514945416745434d42414743797147534962345451454e0a41514946416745454d42414743797147534962345451454e41514947416745424d42414743797147534962345451454e41514948416745414d424147437971470a534962345451454e41514949416745464d42414743797147534962345451454e4151494a416745414d42414743797147534962345451454e4151494b416745410a4d42414743797147534962345451454e4151494c416745414d42414743797147534962345451454e4151494d416745414d42414743797147534962345451454e0a4151494e416745414d42414743797147534962345451454e4151494f416745414d42414743797147534962345451454e41514950416745414d424147437971470a534962345451454e41514951416745414d42414743797147534962345451454e415149524167454c4d42384743797147534962345451454e41514953424241440a41774943424145414251414141414141414141414d42414743697147534962345451454e41514d45416741414d42514743697147534962345451454e415151450a42724441627741414144415042676f71686b69472b45304244514546436745424d42344743697147534962345451454e415159454542427735516e4a682b48780a32634c38483567525a3641775241594b4b6f5a496876684e41513042427a41324d42414743797147534962345451454e415163424151482f4d424147437971470a534962345451454e415163434151482f4d42414743797147534962345451454e415163444151482f4d416f4743437147534d343942414d4341306b414d4559430a4951434d5a4c734b434b594a5a5441464575524f7a45677462596333684b733431703443576c334b614373536b674968414e376d6575686d68794c6f384c62590a415170494c3136396f2f68486c767a3254565a31634b597a383153610a2d2d2d2d2d454e442043455254494649434154452d2d2d2d2d0a2d2d2d2d2d424547494e2043455254494649434154452d2d2d2d2d0a4d4949436c6a4343416a32674177494241674956414a567658633239472b487051456e4a3150517a7a674658433935554d416f4743437147534d343942414d430a4d476778476a415942674e5642414d4d45556c756447567349464e48574342536232393049454e424d526f77474159445651514b4442464a626e526c624342440a62334a7762334a6864476c76626a45554d424947413155454277774c553246756447456751327868636d4578437a414a42674e564241674d416b4e424d5173770a435159445651514745774a56557a4165467730784f4441314d6a45784d4455774d5442614677307a4d7a41314d6a45784d4455774d5442614d484178496a41670a42674e5642414d4d47556c756447567349464e4857434251513073675547786864475a76636d306751304578476a415942674e5642416f4d45556c75644756730a49454e76636e4276636d4630615739754d5251774567594456515148444174545957353059534244624746795954454c4d416b474131554543417743513045780a437a414a42674e5642415954416c56544d466b77457759484b6f5a497a6a3043415159494b6f5a497a6a304441516344516741454e53422f377432316c58534f0a3243757a7078773734654a423732457944476757357258437478327456544c7136684b6b367a2b5569525a436e71523770734f766771466553786c6d546c4a6c0a65546d693257597a33714f42757a43427544416642674e5648534d4547444157674251695a517a575770303069664f44744a5653763141624f536347724442530a42674e5648523845537a424a4d45656752614244686b466f64485277637a6f764c324e6c636e52705a6d6c6a5958526c63793530636e567a6447566b633256790a646d6c6a5a584d75615735305a577775593239744c306c756447567355306459556d397664454e424c6d526c636a416442674e5648513445466751556c5739640a7a62306234656c4153636e553944504f4156634c336c517744675944565230504151482f42415144416745474d42494741315564457745422f7751494d4159420a4166384341514177436759494b6f5a497a6a30454177494452774177524149675873566b6930772b6936565947573355462f32327561586530594a446a3155650a6e412b546a44316169356343494359623153416d4435786b66545670766f34556f79695359787244574c6d5552344349394e4b7966504e2b0a2d2d2d2d2d454e442043455254494649434154452d2d2d2d2d0a2d2d2d2d2d424547494e2043455254494649434154452d2d2d2d2d0a4d4949436a7a4343416a53674177494241674955496d554d316c71644e496e7a6737535655723951477a6b6e42717777436759494b6f5a497a6a3045417749770a614445614d4267474131554541777752535735305a5777675530645949464a766233516751304578476a415942674e5642416f4d45556c756447567349454e760a636e4276636d4630615739754d5251774567594456515148444174545957353059534244624746795954454c4d416b47413155454341774351304578437a414a0a42674e5642415954416c56544d423458445445344d4455794d5445774e4455784d466f58445451354d54497a4d54497a4e546b314f566f77614445614d4267470a4131554541777752535735305a5777675530645949464a766233516751304578476a415942674e5642416f4d45556c756447567349454e76636e4276636d46300a615739754d5251774567594456515148444174545957353059534244624746795954454c4d416b47413155454341774351304578437a414a42674e56424159540a416c56544d466b77457759484b6f5a497a6a3043415159494b6f5a497a6a3044415163445167414543366e45774d4449595a4f6a2f69505773437a61454b69370a314f694f534c52466857476a626e42564a66566e6b59347533496a6b4459594c304d784f346d717379596a6c42616c54565978465032734a424b357a6c4b4f420a757a43427544416642674e5648534d4547444157674251695a517a575770303069664f44744a5653763141624f5363477244425342674e5648523845537a424a0a4d45656752614244686b466f64485277637a6f764c324e6c636e52705a6d6c6a5958526c63793530636e567a6447566b63325679646d6c6a5a584d75615735300a5a577775593239744c306c756447567355306459556d397664454e424c6d526c636a416442674e564851344546675155496d554d316c71644e496e7a673753560a55723951477a6b6e4271777744675944565230504151482f42415144416745474d42494741315564457745422f7751494d4159424166384341514577436759490a4b6f5a497a6a3045417749445351417752674968414f572f35516b522b533943695344634e6f6f774c7550524c735747662f59693747535839344267775477670a41694541344a306c72486f4d732b586f356f2f7358364f39515778485241765a55474f6452513763767152586171493d0a2d2d2d2d2d454e442043455254494649434154452d2d2d2d2d0a0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000".to_string(),
        };

        // Verify the quote
        client
            .verify_quote_from_pccs(&quote_response)
            .await
            .unwrap();
    }
}
