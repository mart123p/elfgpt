import logging

from redis import Redis
from server.keys import *
from server.models.lock import RedisLock

DEFAULT_ALLOW_TTL = 5 # 5 seconds before it expires

class AllowListModel:
    def __init__(self, redis: Redis, lock: RedisLock):
        self.__r = redis
        self.__lock = lock
    
    def insert(self, socket_id: str):
        """
        Insert in a transaction the socket in the allowlist
        """
        self.__lock.lock_r()
        try:
            with self.__r.pipeline() as pipe:
                pipe.sadd(REDIS_GPU_TASK_ALLOWED_SET, socket_id)
                pipe.set(self.__key_ttl(socket_id), 1, ex=DEFAULT_ALLOW_TTL)
                pipe.execute()
        finally:
            self.__lock.release_r()
        
    def present(self, socket_id: str) -> bool:
        """
        Check if a socket id is in set and is allowed. Will remove it if present.

        Returns:
        If allowed
        """
        present = False
        self.__lock.lock_r()
        try:
            result = None
            with self.__r.pipeline() as pipe:
                pipe.multi()
                pipe.delete(self.__key_ttl(socket_id))
                pipe.srem(REDIS_GPU_TASK_ALLOWED_SET, socket_id)
                result = pipe.execute()
            if result == None:
                raise ValueError("Value should not be null")
            present = result[0] > 0
        finally:
            self.__lock.release_r()
        return present

    def delete(self, socket_id: str) -> bool:
        """
        Removes the key from the allowed list
        
        Returns:
        If the key was present in the set and is not expired
        """
        result = None
        self.__lock.lock_r()
        try:
            with self.__r.pipeline() as pipe:
                pipe.delete(self.__key_ttl(socket_id))
                pipe.srem(REDIS_GPU_TASK_ALLOWED_SET, socket_id)
                result = pipe.execute()
        finally:
            self.__lock.release_r()

        if result != None and int(result[1]) > 0:
            return True # The socket id was in the allowed list
        return False
    
    def reconciliation(self) -> int:
        """
        Perform a reconciliation of the keys present in the allowlist
        and the expired keys.

        Returns:
        The amount of key that are not present in the set (expired keys)
        """

        count = 0
        self.__lock.lock_r()
        try:
            members = self.__r.smembers(REDIS_GPU_TASK_ALLOWED_SET)
            for member in members:
                exists = self.__r.exists(self.__key_ttl(member.decode("ascii")))
                if not exists:
                    self.__r.srem(REDIS_GPU_TASK_ALLOWED_SET, member) # We remove it from the allowlist
                    count += 1
        finally:
            self.__lock.release_r()
        
        return count

    def __key_ttl(self, socket_id: str) -> str:
        return REDIS_GPU_TASK_ALLOWED_SET_TTL + socket_id