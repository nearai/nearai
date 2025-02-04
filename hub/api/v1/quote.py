import logging

from fastapi import APIRouter
from quote.quote import Quote

v1_router = APIRouter()
logger = logging.getLogger(__name__)
quote = Quote()


@v1_router.get("/quote")
def get_quote():
    quote.get_quote()
    return quote
