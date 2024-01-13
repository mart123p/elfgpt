from re import Match
from flask_socketio import SocketIO

from server.controller.containers import ContainersController
from workers.worker_gpu.plugins.context import PluginsContext
from workers.worker_gpu.plugins.base import PluginBase

class PluginList(PluginBase):
    def __init__(self, socket_io: SocketIO, socket_id: str, context: PluginsContext, containers: ContainersController):
        self.__containers = containers
        self.__socket_id = socket_id
        super().__init__(r"!list\(\)", socket_io, socket_id, context)

    def _execute(self, message: str, match: Match[str]):
        net_id = self.__containers.get_or_create_net_id(self.__socket_id)
        response = self._http_request(net_id, action="list", file="")
        self._send_message(response)