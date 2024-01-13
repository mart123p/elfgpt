from workers.common.conf import *
from workers.common.imports import *
from workers.worker_gpu.gpu import GpuTask
from server.models.lock import RedisLock
from server.keys import REDIS_GPU_TASK_LOCK

lock = RedisLock(r, REDIS_GPU_TASK_LOCK)
task = GpuTask(celery, r, socket_io, lock)

@worker_ready.connect
def init_worker(**kwargs):
    task.worker_ready(kwargs["sender"].controller.concurrency)

@worker_shutting_down.connect
def stop_worker(**kwargs):
    task.worker_stop()

@worker_process_init.connect
def init_per_process(**kwargs):
    task.process_init()

@celery.task(name="gpu.compute", bind=True)
def gpu_compute(self, message_request_json: str, socket_id: str):
    task.compute(message_request_json, socket_id, self.request.id)
