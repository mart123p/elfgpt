from redis import Redis
from server.keys import REDIS_GPU_TASK_COMMITTED_WORK, REDIS_GPU_TASK_COUNT

class GpuTaskModel:
    
    def __init__(self, redis: Redis):
        self.__r = redis

    def init(self, concurrency):
        """
        Increment the instance of GPU_TASK
        """
        self.__r.incr(REDIS_GPU_TASK_COUNT, concurrency)

    def done(self):
        """
        Decrement committed work.
        """
        self.__r.decr(REDIS_GPU_TASK_COMMITTED_WORK)


    def stop(self, concurrency: int):
        """
        Decrement the instance of GPU_TASK
        """
        self.__r.decr(REDIS_GPU_TASK_COUNT, concurrency)