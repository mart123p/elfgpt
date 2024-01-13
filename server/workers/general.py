from workers.common.conf import *
from workers.common.imports import *
from workers.worker_general.tick import TickTask
from workers.worker_general.containers import ContainersTask
from server.models.lock import RedisLock
from server.keys import REDIS_GPU_TASK_LOCK

lock = RedisLock(r, REDIS_GPU_TASK_LOCK)
tick_task = TickTask(r, socket_io, lock)
containers_task = ContainersTask(r, celery)

@worker_ready.connect
def init_worker(**kwargs):
    tick_task.worker_ready(kwargs["sender"].controller.concurrency)

@worker_shutting_down.connect
def stop_worker(**kwargs):
    tick_task.worker_stop()

@worker_process_init.connect
def init_per_process(**kwargs):
    tick_task.process_init()
    containers_task.process_init()

@celery.task(name="common.allow_list_reconciliation")
def allow_list_reconciliation():
    tick_task.allow_list_reconciliation()


@celery.task(name="common.queue_reconciliation")
def queue_reconciliation():
    tick_task.queue_reconciliation()


@celery.task(name="common.containers.desired_state")
def containers_desired_state():
    containers_task.desired_state()

@celery.task(name="common.containers.create")
def containers_create(net_id: str):
    containers_task.create(net_id)

@celery.task(name="common.containers.shutdown")
def containers_shutdown():
    containers_task.shutdown()

@celery.task(name="common.containers.delete")
def containers_delete(socket_id: str, net_id: str):
    containers_task.delete(socket_id, net_id)