import logging
import subprocess

from fastapi import APIRouter
from quote.quote import Quote

quote_router = APIRouter()
logger = logging.getLogger(__name__)
quote = Quote()


@quote_router.get("/quote")
def get_quote():
    # Get SSL public key hash
    cmd = """echo | openssl s_client -connect localhost:443 2>/dev/null |\
     openssl x509 -pubkey -noout -outform DER | openssl dgst -sha256"""
    ssl_pub_key = subprocess.check_output(cmd, shell=True).decode("utf-8").split("= ")[1].strip()
    logger.info(f"Using SSL public key hash: {ssl_pub_key}")

    # Get quote with SSL public key as message
    quote_result = quote.get_quote(ssl_pub_key)
    return quote_result
