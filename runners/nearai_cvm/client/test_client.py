from runners.nearai_cvm.client.client import CvmClient


def test_attest():
    client = CvmClient("http://localhost:4433")
    quote = client.attest()
    print(quote)


if __name__ == "__main__":
    test_attest()
