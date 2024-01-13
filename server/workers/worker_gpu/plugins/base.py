import os
import re
import logging
import requests
import urllib.parse

from re import Match
from abc import ABC, abstractmethod
from dataclasses import dataclass

from flask_socketio import SocketIO

from server.environ import ENV_NAME_NGINX_BRIDGE_HOSTNAME, NGINX_BRIDGE_HOSTNAME, \
    ENV_NAME_NGINX_BRIDGE_PORT, NGINX_BRIDGE_PORT, ENV_NAME_NGINX_BRIDGE_USERNAME, \
    NGINX_BRIDGE_USERNAME, ENV_NAME_NGINX_BRIDGE_PASSWORD, NGINX_BRIDGE_PASSWORD
from server.dtos import MessageResponse, EVENT_MESSAGE_RESPONSE
from workers.worker_gpu.plugins.context import PluginsContext

BANNER_TOP = "==================== PLUGINS ===================="
BANNER_BOT = "================== END PLUGINS =================="

@dataclass
class PluginConf:
    hostname: str
    port: int
    username: str
    password: str

class PluginBase(ABC):
    def __init__(self, regex_trigger: str, socket_io: SocketIO, socket_id: str, context: PluginsContext):
        self.__regex = regex_trigger
        self.__socket_io = socket_io
        self.__socket_id = socket_id
        self.__context = context
        self.__conf = PluginConf(
            hostname= os.environ.get(ENV_NAME_NGINX_BRIDGE_HOSTNAME, NGINX_BRIDGE_HOSTNAME),
            port= int(os.environ.get(ENV_NAME_NGINX_BRIDGE_PORT, NGINX_BRIDGE_PORT)),
            username= os.environ.get(ENV_NAME_NGINX_BRIDGE_USERNAME, NGINX_BRIDGE_USERNAME),
            password= os.environ.get(ENV_NAME_NGINX_BRIDGE_PASSWORD, NGINX_BRIDGE_PASSWORD)
        )
        self.__logger = logging.getLogger(__name__)

    @abstractmethod
    def _execute(self, message: str, match: Match[str]):
        pass

    def execute(self, message: str):
        matches = re.finditer(self.__regex, message)
        for match_obj in matches:
            if match_obj != None:
                if not self.__context.has_executed():
                    self._send_message("\n"+ BANNER_TOP)

                self.__logger.info("Plugin trigger detected on %s. Running plugin", self.__class__.__name__)
                self._send_message(f"[+] Running command: {match_obj.group(0)}")

                self._execute(message, match_obj)

                self._send_message(f"[+] Finished command: {match_obj.group(0)}")
                self.__logger.info("Plugin finished running")

                self.__context.set_executed()
    
    def _send_message(self, message: str):
        message_response = MessageResponse(message + '\n', False, False)
        self.__socket_io.emit(EVENT_MESSAGE_RESPONSE,message_response.to_json(), to=self.__socket_id)

    def _http_request(self, net_id: str, action: str, file: str) -> str:
        url = f"http://{self.__conf.hostname}:{self.__conf.port}/{net_id}/?"
        params = {'action': action}
        if file != "":
            params['file'] = file

        url += urllib.parse.urlencode(params)
        session = requests.session()
        session.auth = (self.__conf.username, self.__conf.password)

        try:
            response = session.get(url, timeout=3, allow_redirects=False)
            if response.status_code != 200:
                return f"Server returned an error code: {response.status_code}"
            return response.content.decode('utf-8', errors='backslashreplace')
        except requests.exceptions.Timeout:
            return "Server timeout more than 3 seconds..."
        
            