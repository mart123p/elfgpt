import logging

from celery import Celery
from server.models.containers import ContainersModel

class ContainersController:
    def __init__(self, celery: Celery, containers_model: ContainersModel):
        self.__celery = celery
        self.__containers_model = containers_model
        self.__logger = logging.getLogger(__name__)

    def delete(self, socket_id: str):
        """
        Launch a task if a net_id  is associated with a socket_id
        """
        net_id = self.__containers_model.get_net_id(socket_id)
        if net_id != None:
            self.__logger.info("User %s removed. Requesting net_id %s delete", socket_id, net_id)
            self.__celery.send_task("common.containers.delete", args=[socket_id, net_id])
        else:
            # We delete the TTL because it is always set by heartbeat
            self.__containers_model.del_ttl(socket_id)

    def create(self):
        """
        Launch a task to create a new container in the ready pool.
        """
        net_id = self.__containers_model.new_net_id()
        self.__logger.info("Sending task to create net_id %s", net_id)
        self.__celery.send_task("common.containers.create", args=[net_id])

    def get_or_create_net_id(self, socket_id: str) -> str:
        """
        Get the current net_id or request a net_id from the pool and associate it with the pool

        Returns: 
        A newly received net_id
        """
        net_id = self.__containers_model.get_net_id(socket_id)
        if net_id != None:
            return net_id
        
        net_id = self.__containers_model.request_net_id()
        self.__containers_model.associate(socket_id, net_id)
        self.create()
        return net_id
    
    def shutdown(self):
        self.__logger.info("Shutdown requested for containers.")
        self.__containers_model.set_shutdown()
        
        associations = self.__containers_model.get_associations()
        ready = self.__containers_model.get_ready()
        total = len(associations) + len(ready)
        self.__logger.info("Requesting stop for %d containers", total)

        for association in associations:
            self.__celery.send_task("common.containers.delete", args=[association.net_id])

        for net_id in ready:
            # No socket_id this is fine because some keys will simply not be deleted.
            self.__celery.send_task("common.containers.delete", args=["",net_id])
        
        self.__logger.info("All shutdown requests were sent.")
    