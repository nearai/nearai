from typing import Dict, List

from dotenv import load_dotenv
from fastapi import APIRouter
from nearai.evaluation import evaluation_table
from pydantic import BaseModel

load_dotenv()

v1_router = APIRouter(
    prefix="/evaluation",
    tags=["evaluation"],
)


class EvaluationTable(BaseModel):
    rows: List[Dict[str, str]]
    columns: List[str]
    important_columns: List[str]


@v1_router.get("/table")
async def table() -> EvaluationTable:
    rows, columns, important_columns = evaluation_table()
    list_rows = [
        {**dict(key_tuple), **{m: metrics[m] for m in columns if metrics.get(m)}} for key_tuple, metrics in rows.items()
    ]
    return EvaluationTable(rows=list_rows, columns=columns, important_columns=important_columns)
