from abc import abstractmethod
class BaseTask:
    @abstractmethod
    def worker_ready(self, concurrency: int):
        pass

    @abstractmethod
    def worker_stop(self):
        pass

    @abstractmethod
    def process_init(self):
        pass

    