import logging
import os
import random
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from attestation.client import CvmClient
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Store current directory to restore later
    original_dir = os.getcwd()

    try:
        # Get SDK path from environment variable
        sdk_path = os.getenv("PRIVATE_ML_SDK_PATH")
        if not sdk_path:
            logger.error("PRIVATE_ML_SDK_PATH environment variable not set")
            os._exit(1)

        # Navigate to scripts directory
        scripts_path = Path(sdk_path) / "meta-dstack-nvidia/scripts/bin"
        if scripts_path.exists():
            # Add scripts directory to PATH
            os.environ["PATH"] = f"{os.path.abspath(scripts_path)}:{os.environ.get('PATH', '')}"
            logger.info(f"Added {scripts_path} to PATH")
        else:
            logger.error(f"Scripts path {scripts_path} does not exist")
            os._exit(1)
        app.state.app_state.update_pool()

        app.state.app_state.update_pool()

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


class State(BaseModel):
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
                        os.getenv("PRIVATE_ML_SDK_PATH") + "/runner.yaml",
                        "-o",
                        runner_id,
                        "--image",
                        os.getenv("PRIVATE_ML_SDK_PATH") + "/images/dstack-nvidia-dev-0.3.3",
                        "-c",
                        "2",
                        "-m",
                        "4G",
                        "-d",
                        "30G",
                        "--port",
                        f"tcp:0.0.0.0:{worker.port+1}:22",  # TODO: disable SSH
                        "--port",
                        f"tcp:0.0.0.0:{worker.port}:443",
                    ],
                    check=True,
                )

                process = subprocess.Popen(
                    [
                        "sudo",
                        "dstack",
                        "run",
                        runner_id,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                logger.info(f"Started worker {runner_id} (PID: {process.pid})")

                self.free_workers.append(worker)
                logger.info(f"Successfully added worker {runner_id} to pool")
            except Exception as e:
                logger.error(f"Failed to create worker {runner_id}: {str(e)}")

    def pop_available_worker(self) -> Optional[Worker]:
        """Get a worker from the pool."""
        for idx, worker in enumerate(self.free_workers):
            logger.info(f"Checking health of worker {worker.runner_id}")
            client = CvmClient(f"https://localhost:{worker.port}")
            try:
                health = client.is_assigned()
                logger.info(f"Health of worker {worker.runner_id}: {health}")

                if not health.is_assigned:
                    logger.info(f"Found available worker {worker.runner_id}")
                    return self.free_workers.pop(idx)

            except Exception as e:
                logger.error(f"Failed to get health of worker {worker.runner_id}: {str(e)}")
        return None


app.state.app_state = State(free_workers=[], assigned_workers=[], max_pool_size=1)


def get_app_state() -> State:
    return app.state.app_state


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.post("/get_worker")
def get_worker(background_tasks: BackgroundTasks, pool: State = Depends(get_app_state)) -> Optional[Worker]:
    # Get a worker from the pool, TODO: auth
    logger.info(f"Getting worker from pool: {pool.free_workers}")
    if not pool.free_workers:
        logger.warning("No free workers available in pool")
        # You might want to add error handling here

    worker = pool.pop_available_worker()
    if worker is None:
        logger.warning("No free workers available in pool")
        return None
    worker.assigned_at = datetime.now()
    pool.assigned_workers.append(worker)

    logger.info(f"Assigned worker {worker.runner_id} at {worker.assigned_at}")

    background_tasks.add_task(pool.update_pool)

    return worker
