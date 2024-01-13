import logging

from flask_socketio import SocketIO

from server.models.queue import QueueModel
from server.models.allow_list import AllowListModel
from server.dtos import CapacityResponse, EVENT_CAPACITY_RESPONSE, ROOM_CAPACITY_BROADCAST


QUEUE_TTL = 10

class CapacityController:
    def __init__(self, socket_io: SocketIO, queue_model: QueueModel, allow_list_model: AllowListModel):
        self.__socket_io = socket_io
        self.__queue = queue_model
        self.__allow_list = allow_list_model
        self.__logger = logging.getLogger(__name__)
    
    def pick_next(self):
        next = self.__queue.next()
        if next[0]:
            queue_size = next[1]
            socket_id = next[2]

            # We picked out the next user
            self.__logger.info("Next socket id: %s", socket_id)
            capacity_response = CapacityResponse(queue_size, -1, True)
            self.__socket_io.emit(EVENT_CAPACITY_RESPONSE, capacity_response.to_json(), to=socket_id)
            self.__socket_io.server.leave_room(socket_id, ROOM_CAPACITY_BROADCAST)

            # We can send the update to everyone.
            capacity_response = CapacityResponse(queue_size, -1, False)
            self.__socket_io.emit(EVENT_CAPACITY_RESPONSE, capacity_response.to_json(), to=ROOM_CAPACITY_BROADCAST)
        else:
            self.__logger.info("No socket id is available")
    
    def new(self, socket_id):
        result = self.__queue.insert(socket_id)
        queue_size = result[0]
        gpu_tasks_count = result[1]
        committed_work = result[2]

        if committed_work < 0:
            raise ValueError("Not supposed to be less than zero")

        # We register the user in the room
        self.__logger.info("Socket id %s added to queue", socket_id)
        capacity_response = CapacityResponse(queue_size, 0, False)
        self.__socket_io.emit(EVENT_CAPACITY_RESPONSE, capacity_response.to_json(), to=socket_id)

        self.__socket_io.server.enter_room(socket_id, ROOM_CAPACITY_BROADCAST)

        if queue_size - 1 + committed_work < gpu_tasks_count:
            self.__logger.info("Less members in queue (%d) compared to count of GPU tasks (%d)", queue_size, gpu_tasks_count)            
            self.pick_next()

    def delete(self, socket_id):
        self.__queue.delete(socket_id)
        present = self.__allow_list.delete(socket_id)
        if present:
            # We have more capacity since it was in the allow list
            self.pick_next()