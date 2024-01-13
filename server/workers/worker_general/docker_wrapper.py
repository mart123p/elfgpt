import os
import logging

from docker.client import DockerClient
from docker.errors import NotFound
from docker.models.networks import Network
from docker.models.containers import Container

from dataclasses import dataclass
from enum import Enum
from server.environ import ENV_NAME_DOCKER_SOCKET, DOCKER_SOCKET, \
    ENV_NAME_CONTAINER_NGINX_BRIDGE, NGINX_BRIDGE_NAME, \
    ENV_NAME_CHALLENGE_CONTAINER_NAME_PHP, CHALLENGE_PHP_CONTAINER_NAME, \
    ENV_NAME_CHALLENGE_CONTAINER_IMAGE_PHP, CHALLENGE_PHP_CONTAINER_IMAGE, \
    ENV_NAME_CHALLENGE_CONTAINER_NAME_REDIS, CHALLENGE_REDIS_CONTAINER_NAME, \
    ENV_NAME_CHALLENGE_CONTAINER_IMAGE_REDIS, CHALLENGE_REDIS_CONTAINER_IMAGE, \
    ENV_NAME_CHALLENGE_NETWORK, CHALLENGE_NETWORK_NAME

class ChangeState(Enum):
    REDIS_ONLY = 1
    DOCKER_ONLY = 2
    MISSING_A_CONTAINER = 3 # Of the two containers one of them is missing

@dataclass
class DockerSyncChange:
    state: ChangeState
    net_id: str

@dataclass
class DockerChallengeConf:
    nginx_bridge_name: str

    php_name: str
    php_image: str
    redis_name: str
    redis_image: str
    network: str

class DockerWrapper:
    def __init__(self):
        self.__docker_socket = os.environ.get(ENV_NAME_DOCKER_SOCKET, DOCKER_SOCKET)
        self.__conf = self.__get_config()
        self.__client = None
        self.__logger = logging.getLogger(__name__)

    def connect(self):
        """
        Connect to the docker daemon
        """
        self.__client = DockerClient(base_url=self.__docker_socket)
        self.__logger.info("Connected to docker socket.")

    def sync(self, net_ids: list[str]) -> list[DockerSyncChange]:
        """
        Syncs the net_ids and returns a list of changes that need to be performed to get in sync.
        """
        containers_host = {}
        containers = self.__client.containers.list()
        for container in containers:
            name = str(container.name)
            net_id = ""
            if name.startswith(self.__conf.php_name):
                net_id = name.replace(self.__conf.php_name, "")
            if name.startswith(self.__conf.redis_name):
                net_id = name.replace(self.__conf.redis_name, "")

            if net_id != "":
                if not net_id in containers_host:
                    containers_host[net_id] = 1
                else:
                    containers_host[net_id] += 1

        changes = list()
        for net_id in net_ids:
            if net_id not in containers_host:
                change = DockerSyncChange(ChangeState.REDIS_ONLY, net_id)
                changes.append(change)
                continue

            elif containers_host[net_id] < 2:
                change = DockerSyncChange(ChangeState.MISSING_A_CONTAINER, net_id)
                changes.append(change)
            
            containers_host.pop(net_id)
        
        for net_id in containers_host:
            change = DockerSyncChange(ChangeState.DOCKER_ONLY, net_id)
            
            # If the are reused, we make sure to reconnect them to the bridge
            self.__assign_network(net_id) 
            changes.append(change)
        
        if len(changes) > 0:
            self.__logger.warning("Found inconsistencies in docker state: %s", str(changes))
        
        return changes
        
    def create(self, net_id: str):
        network_name = self.__assign_network(net_id).name

        # Create the actual containers
        environment = {'REDIS_HOSTNAME':self.__conf.redis_name + net_id}
        self.__create_container(self.__conf.php_name, net_id, self.__conf.php_image, network_name, environment=environment)
        self.__create_container(self.__conf.redis_name, net_id, self.__conf.redis_image, network_name)

    def remove(self, net_id: str):
        network_name = self.__conf.network + net_id
        network = self.__get_network(network_name) #type: Network
        if network != None:
            nginx = self.__client.containers.get(self.__conf.nginx_bridge_name)
            try:
                network.disconnect(nginx)
            except Exception as e:
                self.__logger.warning("Could not disconnect nginx-bridge from the network: %s", str(e))
        
        self.__remove_container(self.__conf.php_name, net_id)
        self.__remove_container(self.__conf.redis_name, net_id)

        if network != None:
            network.remove()
        

    def __get_network(self, network_name: str) -> Network:
        try:
            network = self.__client.networks.get(network_name)
            return network
        except NotFound:
            return None
    
    def __get_container(self, container_name: str) -> Container:
        try:
            container = self.__client.containers.get(container_name)
            return container
        except NotFound:
            return None
    
    def __assign_network(self, net_id: str) -> Network:
        network_name = self.__conf.network + net_id
        network = self.__get_network(network_name)
        if network == None:
            network = self.__client.networks.create(network_name, driver="bridge") #type: Network

        #Mount the network to the nginx bridge one
        nginx = self.__client.containers.get(self.__conf.nginx_bridge_name)
        try:
            network.connect(nginx)
        except Exception as e:
            self.__logger.warning("Could not connect nginx-bridge to the network: %s", str(e))
        return network
    
    def __create_container(self, container_base_name: str, net_id: str, image_name: str, network_name: str, environment: dict = None):
        container_name = container_base_name + net_id
        self.__client.containers.run(image=image_name, name=container_name, mem_limit="128m", cpu_shares=128, network=network_name, environment=environment, detach=True)
        self.__logger.info("Created container %s with image %s", container_name, image_name)

    def __remove_container(self, container_base_name: str, net_id: str):
        container_name = container_base_name + net_id
        container = self.__get_container(container_name)
        if container != None:
            try:
                container.kill()
                self.__logger.info("Killed container %s", container_name)
            except Exception as e:
                self.__logger.warning("Could not kill container %s Reason: %s", container_name, str(e))

            try:
                container.remove()
                self.__logger.info("Removed container %s", container_name)
            except Exception as e:
                self.__logger.warning("Could not remove container %s Reason: %s", container_name, str(e))
        
        else:
            self.__logger.warning("The container %s was not found. It's already deleted", container_name)

    def __get_config(self) -> DockerChallengeConf:
        nginx_bridge_name = os.environ.get(ENV_NAME_CONTAINER_NGINX_BRIDGE, NGINX_BRIDGE_NAME)

        php_name = os.environ.get(ENV_NAME_CHALLENGE_CONTAINER_NAME_PHP, CHALLENGE_PHP_CONTAINER_NAME)
        php_image = os.environ.get(ENV_NAME_CHALLENGE_CONTAINER_IMAGE_PHP, CHALLENGE_PHP_CONTAINER_IMAGE)
        redis_name = os.environ.get(ENV_NAME_CHALLENGE_CONTAINER_NAME_REDIS, CHALLENGE_REDIS_CONTAINER_NAME)
        redis_image = os.environ.get(ENV_NAME_CHALLENGE_CONTAINER_IMAGE_REDIS, CHALLENGE_REDIS_CONTAINER_IMAGE)
        network = os.environ.get(ENV_NAME_CHALLENGE_NETWORK, CHALLENGE_NETWORK_NAME)

        return DockerChallengeConf(
            nginx_bridge_name,
            php_name,
            php_image,
            redis_name,
            redis_image,
            network)