from attestation.client import CvmClient


def test_attest():
    # Create client - it will automatically fetch and store the server's certificate
    client = CvmClient("https://localhost:4433")

    # Any request will automatically trigger attestation if needed
    health = client.is_assigned()
    print("Health check (with automatic attestation):", health)

    # You can also manually trigger attestation if needed
    quote = client.attest()
    print("Manual attestation result:", quote)


if __name__ == "__main__":
    test_attest()
