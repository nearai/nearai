import logging
import os
import random
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Store current directory to restore later
    original_dir = os.getcwd()

    try:
        # Navigate to scripts directory
        scripts_path = Path("private-ml-sdk/meta-dstack-nvidia/scripts/bin")
        if scripts_path.exists():
            # Add scripts directory to PATH
            os.environ["PATH"] = f"{os.path.abspath(scripts_path)}:{os.environ.get('PATH', '')}"
            logger.info(f"Added {scripts_path} to PATH")
        else:
            logger.error(f"Scripts path {scripts_path} does not exist")
            os._exit(1)

    finally:
        # Restore original directory
        os.chdir(original_dir)
    yield


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)


class Worker(BaseModel):
    port: int
    assigned_at: Optional[datetime]
    runner_id: Optional[str]


class Pool(BaseModel):
    free_workers: List[Worker]
    assigned_workers: List[Worker]
    max_pool_size: int

    def update_pool(self):
        """Update the pool of workers."""
        # TODO: Fix port collisions
        missing_workers = self.max_pool_size - len(self.free_workers)
        if missing_workers > 0:
            logger.info(f"Adding {missing_workers} workers to pool")

        for _ in range(missing_workers):
            port = random.randint(10000, 65535)
            runner_id = f"nearai-cvm-{port}"
            worker = Worker(port=port, assigned_at=None, runner_id=runner_id)

            logger.info(f"Creating new worker with runner_id: {runner_id}, port: {port}")
            try:
                subprocess.run(
                    [
                        "dstack",
                        "new",
                        "runner.yaml",
                        "-o",
                        runner_id,
                        "--image",
                        "images/dstack-nvidia-dev-0.3.3",
                        "-c",
                        "2",
                        "-m",
                        "4G",
                        "-d",
                        "30G",
                        "--port",
                        "tcp:10022:22",  # TODO: disable SSH
                        "--port",
                        "tcp:8888:8888",
                        "--port",
                        f"tcp:{worker.port}:{worker.port}",
                    ]
                )
                self.free_workers.append(worker)
                logger.info(f"Successfully added worker {runner_id} to pool")
            except Exception as e:
                logger.error(f"Failed to create worker {runner_id}: {str(e)}")


app.state.app_state = Pool(free_workers=[], assigned_workers=[], max_pool_size=10)


def get_app_state() -> Pool:
    return app.state.app_state


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.post("/get_worker")
def get_worker(background_tasks: BackgroundTasks, pool: Pool = Depends(get_app_state)):
    # Get a worker from the pool, TODO: auth
    logger.info(f"Getting worker from pool: {pool.free_workers}")
    if not pool.free_workers:
        logger.warning("No free workers available in pool")
        # You might want to add error handling here

    worker = pool.free_workers.pop()
    worker.assigned_at = datetime.now()
    pool.assigned_workers.append(worker)

    logger.info(f"Assigned worker {worker.runner_id} at {worker.assigned_at}")

    background_tasks.add_task(pool.update_pool)

    return worker
