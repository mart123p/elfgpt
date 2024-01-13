from typing import Tuple
from redis import Redis
from server.keys import *
from server.models.lock import RedisLock
from server.models.allow_list import DEFAULT_ALLOW_TTL

DEFAULT_QUEUE_TTL = 15 #TTL same as timeout

class QueueModel:
    def __init__(self, redis: Redis, lock: RedisLock):
        self.__r = redis
        self.__lock = lock

    
    def length(self) -> int:
        """
        Returns:
        The length of the queue. Does not perform locking, just meant as statistics
        """
        count = self.__r.llen(REDIS_GPU_TASK_QUEUE)
        return count

    def delete(self, socket_id: str) -> bool:
        """
        Removes a socket from the queue. Used for cleanup

        Returns:
        If the key was present in the queue.
        """
        result = 0
        self.__lock.lock_r()
        try:
            result = self.__r.lrem(REDIS_GPU_TASK_QUEUE, 0, socket_id)
            self.__r.delete(self.__key_queue_ttl(socket_id))
        finally:
            self.__lock.release_r()
        return result > 0
    
    def next(self) -> Tuple[bool,int, str]:
        """
        Get the next socket_id in queue and move it to the allow list

        Returns: 
        True if a socket id was moved to allowlist and the current size of the queue
        """
        result = None
        socket_id = None
        self.__lock.lock_r()
        try:
            socket_id = self.__r.rpop(REDIS_GPU_TASK_QUEUE)
            if socket_id == None:
                return False, 0, ""
            socket_id = socket_id.decode("ascii")
            with self.__r.pipeline() as pipe:
                pipe.multi()
                pipe.llen(REDIS_GPU_TASK_QUEUE)
                pipe.sadd(REDIS_GPU_TASK_ALLOWED_SET, socket_id)
                pipe.set(self.__key_allow_ttl(socket_id), 1, ex=DEFAULT_ALLOW_TTL)
                result = pipe.execute()
        finally:
            self.__lock.release_r()
        if result != None:
            return True, int(result[0]), socket_id
        return False, 0, socket_id

    def insert(self, socket_id: str) -> Tuple[int,int]:
        """
        Insert a value in the queue.

        Returns:
        The number of elements in queue. Number of GPU tasks (processes), Comitted work
        """
        result = None
        self.__lock.lock_r()
        try:
            with self.__r.pipeline() as pipe:
                pipe.multi()
                pipe.lpush(REDIS_GPU_TASK_QUEUE, socket_id)
                pipe.set(self.__key_queue_ttl(socket_id), 1, ex=DEFAULT_QUEUE_TTL)
                pipe.get(REDIS_GPU_TASK_COUNT)
                pipe.get(REDIS_GPU_TASK_COMMITTED_WORK)
                result = pipe.execute()
        finally:
            self.__lock.release_r()
        
        if result == None:
            raise ValueError("Expected result to not be none")
        
        if result[2] == None:
            raise ValueError("Expected REDIS_GPU_TASK_COUNT to be present")
        
        if result[3] == None:
            result[3] = 0
        return int(result[0]), int(result[2]), int(result[3])
    
    def touch(self, socket_id: str):
        """
        Mark the entry as still valid
        """
        self.__lock.lock_r()
        try:
            self.__r.set(self.__key_queue_ttl(socket_id), 1, ex=DEFAULT_QUEUE_TTL)
        finally:
            self.__lock.release_r()


    def reconciliation(self) -> int:
        """
        Checks if all the members in list are valid

        Returns:
        Number of removed elements from queue.
        """
        count = 0
        self.__lock.lock_r()
        try:
            members = self.__r.lrange(REDIS_GPU_TASK_QUEUE, 0 , -1)
            for member in members:
                exists = self.__r.exists(self.__key_queue_ttl(member.decode("ascii")))
                if not exists:
                    self.__r.lrem(REDIS_GPU_TASK_QUEUE, 0, member)
                    count += 1
        finally:
            self.__lock.release_r()
        return count

    def __key_queue_ttl(self, socket_id: str) -> str:
        return REDIS_GPU_TASK_QUEUE_TTL + socket_id
    
    def __key_allow_ttl(self, socket_id: str) -> str:
        return REDIS_GPU_TASK_ALLOWED_SET_TTL + socket_id