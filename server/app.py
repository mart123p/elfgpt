import logging
import redis
import os
from flask import Flask, request
from flask_socketio import SocketIO, emit

from server.dtos import *
from server.keys import *
from server.environ import ENV_NAME_SECRET_KEY, ENV_NAME_REDIS, REDIS_URL
from server.models.queue import QueueModel
from server.models.allow_list import AllowListModel
from server.models.cancel import CancelTaskModel
from server.models.lock import RedisLock
from server.controller.capacity import CapacityController
from server.models.containers import ContainersModel
from server.controller.containers import ContainersController
from server.state import FlaskState
from workers.common.conf import celery

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(ENV_NAME_SECRET_KEY, "default")
if app.config['SECRET_KEY'] == "default":
    logger.warning("SECRET_KEY is the default. Make sure you change this in DEV")

socketio = SocketIO(app,
                    cors_allowed_origins="*",
                    logger=True,
                    message_queue=os.environ.get(ENV_NAME_REDIS, REDIS_URL))
r = redis.Redis.from_url(os.environ.get(ENV_NAME_REDIS, REDIS_URL))

redis_lock = RedisLock(r, REDIS_GPU_TASK_LOCK)
queue_model = QueueModel(r, redis_lock)
allow_list_model = AllowListModel(r, redis_lock)
cancel_task_model = CancelTaskModel(r)
containers_model = ContainersModel(r)
containers_controller = ContainersController(celery, containers_model)
capacity_controller = CapacityController(socketio, queue_model, allow_list_model)

challenge_ids = set([1,2,3])
state = {} # type: dict[str, FlaskState]


@socketio.on("connect")
def connect():
    state[request.sid] = FlaskState(task_id="", capacity_requested=False)
    
@socketio.on("disconnect")
def disconnect():
    # TODO potential optimization if a connection is killed and GPU is still responding
    capacity_controller.delete(request.sid)
    containers_controller.delete(request.sid)
    state.pop(request.sid)

@socketio.on(EVENT_HEARTBEAT)
def heartbeat():
    if state[request.sid].capacity_requested:
        queue_model.touch(request.sid)
    containers_model.touch(request.sid)

@socketio.on(EVENT_CAPACITY_REQUEST)
def handle_capacity(json: str):
    capacity_request = CapacityRequest.from_json(json)
    if capacity_request.challenge_id not in challenge_ids:
        raise ValueError("Invalid challenge id")
    
    state[request.sid].task_id = ""
    state[request.sid].capacity_requested = True
    capacity_controller.new(request.sid)

@socketio.on(EVENT_CANCEL_REQUEST)
def handle_cancel():
    task_id = state[request.sid].task_id
    if task_id == "":
        # Remove element from queue.
        capacity_controller.delete(request.sid)
        state[request.sid].capacity_requested = False
        emit(EVENT_CANCEL_RESPONSE)
    else:
        # Set a cancel key
        cancel_task_model.cancel(task_id)
        state[request.sid].task_id = ""

@socketio.on(EVENT_MESSAGE_REQUEST)
def handle_message(json: str):
    message_request = MessageRequest.from_json(json)
    if message_request.challenge_id not in challenge_ids:
        raise ValueError("Invalid challenge id")

    if allow_list_model.present(request.sid):
        state[request.sid].capacity_requested = False

        r.incr(REDIS_GPU_TASK_COMMITTED_WORK)
        result = celery.send_task("gpu.compute", args=[json, request.sid])
        state[request.sid].task_id = result.id # We store the ID if we want to cancel the task
    else:
        raise ValueError("Not authorized. Wait your turn!")

@socketio.on_error()
def error_handler(e: Exception):
    logger.error("Uncaught error was encountered", e, exc_info=True)

    error = ServerErrorResponse(str(e))
    emit(EVENT_SERVER_ERROR, error.to_json())

@app.route('/')
def static_file_index():
    return app.send_static_file("index.html")

@app.errorhandler(404)
def not_found_error(error):
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def static_file(path):
    return app.send_static_file(path)

if __name__ == '__main__':
    # This code is only for the flask dev server
    try:
        redis_lock.start()
        socketio.run(app)
    finally:
        redis_lock.stop()
