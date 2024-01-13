from redis import Redis

from server.keys import REDIS_GPU_TASK_CANCELED

CANCEL_CHECK_FREQUENCY = 4 #In seconds

class CancelTaskModel:

    def __init__(self, redis: Redis):
        self.__r = redis

    def cancel(self, task_id: str):
        """
        Set the key to mark the task as ready to cancel
        """
        self.__r.set(self.__key(task_id), 1)

    def is_canceled(self, task_id: str) -> bool:
        """
        Checks if the task is canceled. Removes the cancel signal once read

        Returns:
        True if the tasks is canceled
        """
        result = self.__r.delete(self.__key(task_id))
        return result > 0
    
    def cleanup(self, task_id: str):
        """
        Remove the cancel message from the database
        """
        self.__r.delete(self.__key(task_id))
    
    def __key(self, task_id: str):
        return REDIS_GPU_TASK_CANCELED + task_id