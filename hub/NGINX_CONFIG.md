When deploying NEAR AI HUB behind the NGINX proxy, configure the following parameters to ensure smooth operation:

Increase the timeouts to prevent 502 Bad Gateway errors for long-running agent processes.
Setting these variables ensures that requests with long processing times (over 60 seconds) are not prematurely terminated:

```
proxy_read_timeout 600s;          # Allow the NGINX proxy to wait up to 600 seconds for the response from the upstream server
proxy_connect_timeout 600s;       # Set the maximum time NGINX waits to establish a connection to the upstream server
proxy_send_timeout 600s;          # Set the maximum time NGINX waits to send data to the upstream server
```

Disable retries to prevent unnecessary retries and potential cascading failures.
These settings ensure that NGINX will not attempt to forward a request to the next upstream server if the first one fails:

```
proxy_next_upstream off;          # Disables retrying the request on the next upstream server if it fails
proxy_next_upstream_tries 1;      # Limits retries to 1 (if any), effectively avoiding additional retries
```

Adjust buffer sizes for better handling of large responses from the upstream server
```
proxy_buffer_size 128k;           # Set the buffer size for the initial response from the upstream server
proxy_buffers 4 256k;             # Set the number and size of buffers for the response
proxy_busy_buffers_size 256k;     # Set the maximum size of buffers that can be used for busy responses
```
