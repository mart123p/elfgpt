from re import Match
from flask_socketio import SocketIO

from server.controller.containers import ContainersController
from workers.worker_gpu.plugins.context import PluginsContext
from workers.worker_gpu.plugins.base import PluginBase

class PluginFile(PluginBase):
    def __init__(self, socket_io: SocketIO, socket_id: str, context: PluginsContext, containers: ContainersController):
        self.__containers = containers
        self.__socket_id = socket_id
        super().__init__(r"!file\('(.+?)'\)", socket_io, socket_id, context)

    def _execute(self, message: str, match: Match[str]):
        argument = match.group(1)
        if argument.lower() == "arg":
            self._send_message("[+] Default argument (ARG). Will not fetch a file.")        
            return
        
        net_id = self.__containers.get_or_create_net_id(self.__socket_id)
        self._send_message(f"[+] Content of file '{argument}' is presented below.")
        response = self._http_request(net_id, action="file", file=match.group(1))
        self._send_message(response)
