import logging

from redis import Redis
from flask_socketio import SocketIO

from server.models.queue import QueueModel
from server.models.allow_list import AllowListModel
from server.models.lock import RedisLock
from server.controller.capacity import CapacityController
from workers.common.base import BaseTask

class TickTask(BaseTask):
    def __init__(self, redis: Redis, socket_io: SocketIO, redis_lock: RedisLock):
        self.__queue_model = QueueModel(redis, redis_lock)
        self.__allow_list_model = AllowListModel(redis, redis_lock)
        self.__capacity_controller = CapacityController(socket_io, self.__queue_model, self.__allow_list_model)
        self.__redis_lock = redis_lock
        self.__logger = logging.getLogger(__name__)

    def worker_ready(self, concurrency: int):
        self.__redis_lock.start(concurrency)

    def worker_stop(self):
        self.__redis_lock.stop()

    def process_init(self):
        pass
    
    def allow_list_reconciliation(self):
        self.__logger.info("allow_list_reconciliation")
        count = self.__allow_list_model.reconciliation()

        self.__logger.info("Removed %d from allow_list", count)
        
        for _ in range(count):
            # We have new capacity
            self.__capacity_controller.pick_next()

    def queue_reconciliation(self):
        self.__logger.info("queue_reconciliation")
        count = self.__queue_model.reconciliation()
        self.__logger.info("Removed %d from queue", count)