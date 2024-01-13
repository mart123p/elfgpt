import logging
import time

from celery import Celery
from redis import Redis
from flask_socketio import SocketIO

from server.dtos import EVENT_MESSAGE_RESPONSE, EVENT_CANCEL_RESPONSE, MessageRequest, MessageResponse
from server.keys import *
from server.controller.capacity import CapacityController
from server.controller.containers import ContainersController
from server.models.queue import QueueModel
from server.models.allow_list import AllowListModel
from server.models.cancel import CancelTaskModel, CANCEL_CHECK_FREQUENCY
from server.models.lock import RedisLock
from server.models.gpu_task import GpuTaskModel
from server.models.containers import ContainersModel
from workers.worker_gpu.plugins.base import BANNER_BOT
from workers.worker_gpu.plugins.context import PluginsContext
from workers.worker_gpu.plugins.commands.list import PluginList
from workers.worker_gpu.plugins.commands.file import PluginFile
from workers.worker_gpu.challenge import ChallengeFactory
from workers.worker_gpu.llm import LlmResponseEnum, LlmWrapper
from workers.common.base import BaseTask

class GpuTask(BaseTask):
    def __init__(self, celery: Celery, redis: Redis, socket_io: SocketIO, redis_lock: RedisLock):
        self.__celery = celery
        self.__socket = socket_io
        self.__logger = logging.getLogger(__name__)
        self.__concurrency = 0
        self.__redis_lock = redis_lock

        self.__cancel_task_model = CancelTaskModel(redis)
        self.__queue_model = QueueModel(redis, redis_lock)
        self.__gpu_task_model = GpuTaskModel(redis)
        allow_list_model = AllowListModel(redis, redis_lock)
        self.__capacity_controller = CapacityController(socket_io, self.__queue_model, allow_list_model)
        self.__containers_controller = ContainersController(self.__celery, ContainersModel(redis))
        self.__llm = LlmWrapper()

        # Used in token_handler
        self.__last_cancel_check = 0
        self.__socket_id = ""
        self.__task_id = ""


    # Executes in the main process
    def worker_ready(self, concurrency: int):
        self.__logger.info("Called worker init")

        self.__concurrency = concurrency
        self.__redis_lock.start(concurrency)
        self.__gpu_task_model.init(self.__concurrency)

        self.__logger.info("Concurrency: %d", self.__concurrency)

    # Executes in the main process
    def worker_stop(self):
        self.__logger.info("Called worker stop")

        self.__gpu_task_model.stop(self.__concurrency)
        self.__redis_lock.stop()
        self.__logger.info("Concurrency: %d", self.__concurrency)

    def process_init(self):
        self.__logger.info("Init task called")

        #It's online pick next
        if self.__queue_model.length() > 0:
            self.__logger.info("Elements in queue, call pick_next()")
            self.__capacity_controller.pick_next()

        self.__llm.setup()
        self.__logger.info("Init done!")


    def __token_handler(self,token: str) -> bool:
        message_response = MessageResponse(token, False, False)
        self.__socket.emit(EVENT_MESSAGE_RESPONSE, message_response.to_json(), to=self.__socket_id)

        # Will need to migrate this check every 4 seconds.
        elapsed_time = time.time() - self.__last_cancel_check
        if elapsed_time > CANCEL_CHECK_FREQUENCY:
            self.__last_cancel_check = time.time()
            needs_cancel = self.__cancel_task_model.is_canceled(self.__task_id)
            if needs_cancel:
                self.__logger.info("Received a cancel request")
                message_response = MessageResponse("", False, True)
                self.__socket.emit(EVENT_MESSAGE_RESPONSE, message_response.to_json(), to=self.__socket_id)
                self.__socket.emit(EVENT_CANCEL_RESPONSE, to=self.__socket_id)
                return False
        return True

    def compute(self, message_request_json: str, socket_id: str, task_id: str):
        self.__logger.info("GPU_compute called %s", socket_id)
        self.__queue_model.delete(socket_id)
        try:
            self.__last_cancel_check = time.time()
            self.__socket_id = socket_id
            self.__task_id = task_id

            
            message_request = MessageRequest.from_json(message_request_json)
            challenge = ChallengeFactory.make(message_request.challenge_id)
            
            plugins_context = PluginsContext()
            plugins = list()
            
            if challenge.has_plugins:
                plugins.append(PluginList(self.__socket, socket_id, plugins_context, self.__containers_controller))
                plugins.append(PluginFile(self.__socket, socket_id, plugins_context, self.__containers_controller))
            
            response = self.__llm.discuss(socket_id, challenge, message_request.content, self.__token_handler, plugins)
            if response == LlmResponseEnum.OK:
                if plugins_context.has_executed():
                    last_line_response = MessageResponse(BANNER_BOT, False, False)
                    self.__socket.emit(EVENT_MESSAGE_RESPONSE, last_line_response.to_json(), to=socket_id)
                    
                message_response = MessageResponse("", False, True)

            elif response == LlmResponseEnum.CANCELLED:
                message_response = None

            elif response == LlmResponseEnum.CLAWEDBACK:
                message_response = MessageResponse(challenge.clawback_appology, True, True)
            
            if message_response != None:
                self.__socket.emit(EVENT_MESSAGE_RESPONSE, message_response.to_json(), to=socket_id)

        finally:
            self.__gpu_task_model.done()
            self.__cancel_task_model.cleanup(task_id)

            self.__capacity_controller.pick_next()
            self.__logger.info("GPU_compute done")
