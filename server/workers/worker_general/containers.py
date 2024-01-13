import logging
import os

from celery import Celery
from redis import Redis

from server.environ import ENV_NAME_CONTAINER_POOL_SIZE, CONTAINER_POOL_SIZE
from server.models.containers import ContainersModel
from server.controller.containers import ContainersController
from workers.common.base import BaseTask
from workers.worker_general.docker_wrapper import DockerWrapper, DockerSyncChange, ChangeState

class ContainersTask(BaseTask):
    def __init__(self, redis: Redis,celeryapp: Celery):
        self.__celery = celeryapp
        self.__containers_model = ContainersModel(redis)
        self.__controller = ContainersController(self.__celery, self.__containers_model)
        self.__logger = logging.getLogger(__name__)
        self.__docker = None

    def worker_ready(self, concurrency: int):
        pass

    def worker_stop(self):
        pass

    def process_init(self):
        self.__docker = DockerWrapper()
        self.__docker.connect()

    def desired_state(self):
        desired_pool_size = int(os.environ.get(ENV_NAME_CONTAINER_POOL_SIZE, CONTAINER_POOL_SIZE))
        if self.__containers_model.is_shutdown():
            self.__logger.info("Shutdown is signaled. Skipping")
            return
        
        # Sync
        # Get the state in redis and find inconsistencies
        associations = self.__containers_model.get_associations()
        ready = self.__containers_model.get_ready()
        redis_net_ids = list()
        
        for net_id in ready:
            redis_net_ids.append(net_id)

        for association in associations:
            redis_net_ids.append(association.net_id)
        
        docker_changes = self.__docker.sync(redis_net_ids)
        for docker_change in docker_changes:
            if docker_change.state == ChangeState.MISSING_A_CONTAINER:
                # We delete it it's wrong
                self.delete("", docker_change.net_id) # Should normally call controller, but it's a weird state

            elif docker_change.state == ChangeState.DOCKER_ONLY:
                self.__containers_model.ready(docker_change.net_id, True)

            elif docker_change.state == ChangeState.REDIS_ONLY:
                self.delete("", docker_change.net_id) # Same here


        # Check if we are missing containers
        queue_size = self.__containers_model.queue_size()
        self.__logger.info("%d queue_size ready | %d desired_pool_size", queue_size, desired_pool_size)
        containers_to_create = desired_pool_size - queue_size
        self.__logger.info("%d containers to create", containers_to_create)
        if containers_to_create > 0:
            for i in range(containers_to_create):
                self.__controller.create()
        
        # Check if some associations are expired
        associations = self.__containers_model.get_associations()
        for association in associations:
            if self.__containers_model.is_association_dead(association.socket_id):
                self.__controller.delete(association.socket_id) # This is better because it sends the task

    def create(self, net_id: str):
        self.__docker.create(net_id)
        self.__logger.info("net_id %s is ready", net_id)
        self.__containers_model.ready(net_id)

    def delete(self, socket_id: str, net_id: str):
        self.__docker.remove(net_id)
        self.__logger.info("socket_id: %s | net_id %s is deleted", socket_id, net_id)
        self.__containers_model.delete_association(socket_id, net_id)        

    def shutdown(self):
        self.__controller.shutdown()