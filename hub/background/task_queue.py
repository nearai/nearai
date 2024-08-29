from fastapi import BackgroundTasks

_background_tasks = None


def set_background_tasks(background_tasks: BackgroundTasks):
    global _background_tasks
    _background_tasks = background_tasks


def queue_task(func, *args, **kwargs):
    if _background_tasks is None:
        raise RuntimeError("Background tasks not initialized")
    _background_tasks.add_task(func, *args, **kwargs)
