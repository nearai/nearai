use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::{Arc, Mutex};
use std::thread;

use serde_json::json;

/// A mock key provider server for testing
pub struct MockKeyProvider {
    addr: String,
    port: u16,
    expected_quote: Arc<Mutex<Vec<u8>>>,
    response: Arc<Mutex<Vec<u8>>>,
    handle: Option<thread::JoinHandle<()>>,
}

impl MockKeyProvider {
    /// Create a new mock key provider server
    pub fn new() -> Self {
        // Start with default values
        Self {
            addr: "127.0.0.1".to_string(),
            port: 0, // Will be assigned by the OS
            expected_quote: Arc::new(Mutex::new(vec![])),
            response: Arc::new(Mutex::new(vec![])),
            handle: None,
        }
    }

    /// Set the expected quote that the server should receive
    pub fn expect_quote(&mut self, quote: Vec<u8>) -> &mut Self {
        *self.expected_quote.lock().unwrap() = quote;
        self
    }

    /// Set the response that the server should send
    pub fn with_response(&mut self, encrypted_key: Vec<u8>, provider_quote: Vec<u8>) -> &mut Self {
        let response = json!({
            "encrypted_key": encrypted_key,
            "provider_quote": provider_quote,
        });
        *self.response.lock().unwrap() = serde_json::to_vec(&response).unwrap();
        self
    }

    /// Start the mock server
    pub fn start(&mut self) -> (String, u16) {
        let listener = TcpListener::bind(format!("{}:0", self.addr)).unwrap();
        let addr = listener.local_addr().unwrap();
        self.port = addr.port();

        let expected_quote = self.expected_quote.clone();
        let response = self.response.clone();

        let handle = thread::spawn(move || {
            for stream in listener.incoming() {
                match stream {
                    Ok(stream) => {
                        let expected_quote = expected_quote.clone();
                        let response = response.clone();
                        thread::spawn(move || {
                            Self::handle_connection(stream, expected_quote, response);
                        });
                    }
                    Err(e) => {
                        eprintln!("Error accepting connection: {}", e);
                    }
                }
            }
        });

        self.handle = Some(handle);
        (self.addr.clone(), self.port)
    }

    fn handle_connection(
        mut stream: TcpStream,
        expected_quote: Arc<Mutex<Vec<u8>>>,
        response: Arc<Mutex<Vec<u8>>>,
    ) {
        // Read length
        let mut length_bytes = [0u8; 4];
        if stream.read_exact(&mut length_bytes).is_err() {
            return;
        }
        let length = u32::from_be_bytes(length_bytes) as usize;

        // Read request data
        let mut request_data = vec![0u8; length];
        if stream.read_exact(&mut request_data).is_err() {
            return;
        }

        // Parse request
        if let Ok(request) = serde_json::from_slice::<serde_json::Value>(&request_data) {
            // Verify the quote matches what we expect
            if let Some(quote) = request["quote"].as_array() {
                let received_quote: Vec<u8> = quote
                    .iter()
                    .map(|v| v.as_u64().unwrap_or(0) as u8)
                    .collect();

                let expected = expected_quote.lock().unwrap();
                if received_quote == *expected {
                    // Send response
                    let response_data = response.lock().unwrap();
                    let response_length = response_data.len() as u32;

                    // Send length as big-endian u32
                    let _ = stream.write_all(&response_length.to_be_bytes());
                    let _ = stream.write_all(&response_data);
                }
            }
        }
    }

    /// Stop the mock server
    pub fn stop(self) {
        if let Some(handle) = self.handle {
            // The server will stop when the TcpListener is dropped
            drop(handle);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};
    use std::net::TcpStream;

    #[test]
    fn test_mock_key_provider() {
        let mut mock = MockKeyProvider::new();

        // Set up the mock
        let expected_quote = vec![1, 2, 3, 4];
        let encrypted_key = vec![5, 6, 7, 8];
        let provider_quote = vec![9, 10, 11, 12];

        mock.expect_quote(expected_quote.clone())
            .with_response(encrypted_key.clone(), provider_quote.clone());

        // Start the mock
        let (addr, port) = mock.start();

        // Connect to the mock
        let mut stream = TcpStream::connect(format!("{}:{}", addr, port)).unwrap();

        // Send a request
        let request = json!({
            "quote": expected_quote,
        });
        let serialized = serde_json::to_vec(&request).unwrap();
        let length = serialized.len() as u32;

        stream.write_all(&length.to_be_bytes()).unwrap();
        stream.write_all(&serialized).unwrap();

        // Read the response
        let mut response_length_bytes = [0u8; 4];
        stream.read_exact(&mut response_length_bytes).unwrap();
        let response_length = u32::from_be_bytes(response_length_bytes) as usize;

        let mut response_data = vec![0u8; response_length];
        stream.read_exact(&mut response_data).unwrap();

        let response: serde_json::Value = serde_json::from_slice(&response_data).unwrap();

        // Verify the response
        let received_encrypted_key: Vec<u8> = response["encrypted_key"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_u64().unwrap() as u8)
            .collect();

        let received_provider_quote: Vec<u8> = response["provider_quote"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_u64().unwrap() as u8)
            .collect();

        assert_eq!(received_encrypted_key, encrypted_key);
        assert_eq!(received_provider_quote, provider_quote);

        // Stop the mock
        mock.stop();
    }
}
