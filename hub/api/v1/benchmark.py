import json
from os import getenv
from typing import List, Optional

import boto3
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Integer, func
from sqlmodel import col, select

from hub.api.v1.auth import AuthToken, get_auth
from hub.api.v1.models import Benchmark, BenchmarkResult, get_session

load_dotenv()
S3_BUCKET = getenv("S3_BUCKET")

S3_ENDPOINT = getenv("S3_ENDPOINT")
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
)

v1_router = APIRouter(
    prefix="/benchmark",
    tags=["benchmark"],
)


def requires_login(auth: AuthToken = Depends(get_auth)):
    return auth.account_id


@v1_router.get("/create")
async def create_benchmark(
    benchmark_name: str,
    solver_name: str,
    solver_args: str,
    namespace: str = Depends(requires_login),
) -> int:
    with get_session() as session:
        benchmark = Benchmark(
            namespace=namespace,
            benchmark=benchmark_name,
            solver=solver_name,
            args=solver_args,
        )
        session.add(benchmark)
        session.commit()
        benchmark_id = benchmark.id
    return benchmark_id


@v1_router.get("/get")
async def get_benchmark(
    namespace: str,
    benchmark_name: str,
    solver_name: str,
    solver_args: str,
) -> int:
    """Get the ID of a benchmark given its attributes.

    Return -1 if the benchmark does not exist.
    """
    with get_session() as session:
        query = (
            select(Benchmark)
            .where(
                Benchmark.namespace == namespace,
                Benchmark.benchmark == benchmark_name,
                Benchmark.solver == solver_name,
                Benchmark.args == solver_args,
            )
            .order_by(col(Benchmark.id).desc())
        )
        benchmark = session.exec(query).first()

        if benchmark is None:
            return -1
        else:
            return benchmark.id


class BenchmarkOutput(BaseModel):
    id: int
    namespace: str
    benchmark: str
    solver: str
    args: str
    solved: int
    total: int


@v1_router.get("/list")
async def list_benchmarks(
    namespace: Optional[str] = None,
    benchmark_name: Optional[str] = None,
    solver_name: Optional[str] = None,
    solver_args: Optional[str] = None,
    total: int = 32,
    offset: int = 0,
) -> List[BenchmarkOutput]:
    query = (
        select(
            Benchmark,
            func.count(BenchmarkResult.benchmark_id),  # type: ignore
            func.sum(func.cast(BenchmarkResult.solved, Integer)),  # type: ignore
        )
        .where(Benchmark.id == BenchmarkResult.benchmark_id)
        .group_by(Benchmark.id)  # type: ignore
    )

    if namespace is not None and namespace != "":
        query = query.where(Benchmark.namespace == namespace)
    if benchmark_name is not None and benchmark_name != "":
        query = query.where(col(Benchmark.benchmark).contains(benchmark_name))
    if solver_name is not None and solver_name != "":
        query = query.where(col(Benchmark.solver).contains(solver_name))
    if solver_args is not None and solver_args != "":
        query = query.where(col(Benchmark.args).contains(solver_args))

    query = query.offset(offset).limit(total)

    with get_session() as session:
        benchmarks = session.exec(query).all()
        assert isinstance(benchmarks, list)

        result = []
        for benchmark, total, solved in benchmarks:
            assert isinstance(benchmark, Benchmark)
            result.append(
                BenchmarkOutput(
                    id=benchmark.id,
                    namespace=benchmark.namespace,
                    benchmark=benchmark.benchmark,
                    solver=benchmark.solver,
                    args=benchmark.args,
                    solved=solved,
                    total=total,
                )
            )
        return result


@v1_router.get("/add_result")
async def add_benchmark_result(
    benchmark_id: int,
    index: int,
    solved: bool,
    info: str,
    namespace: str = Depends(requires_login),
):
    with get_session() as session:
        benchmark_q = select(Benchmark).where(Benchmark.id == benchmark_id)
        benchmark = session.exec(benchmark_q).first()

        if benchmark is None:
            raise HTTPException(status_code=404, detail=f"Benchmark {benchmark_id} not found")

        if benchmark.namespace != namespace:
            raise HTTPException(status_code=403, detail="Not authorized to add result")

        result_q = select(BenchmarkResult).where(
            BenchmarkResult.benchmark_id == benchmark_id,
            BenchmarkResult.index == index,
        )
        result = session.exec(result_q).first()

        if result is not None:
            raise HTTPException(status_code=409, detail=f"Result {index} already exists")

        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            index=index,
            solved=solved,
            info=info,
        )
        session.add(result)
        session.commit()


class BenchmarkResultOutput(BaseModel):
    index: int
    solved: bool
    info: str


@v1_router.get("/get_result")
async def get_benchmark_result(benchmark_id: int) -> List[BenchmarkResultOutput]:
    query = select(BenchmarkResult).where(BenchmarkResult.benchmark_id == benchmark_id)
    with get_session() as session:
        results = session.exec(query).all()
        return [
            BenchmarkResultOutput(
                index=result.index,
                solved=result.solved,
                info=json.dumps(result.info),
            )
            for result in results
        ]
