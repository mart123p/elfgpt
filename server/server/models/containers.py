from redis import Redis
from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin

from server.keys import REDIS_CONTAINERS_ACTIVE_SET, REDIS_CONTAINERS_COUNT_CREATING, REDIS_CONTAINERS_COUNT_KEY, REDIS_CONTAINERS_READY_QUEUE, REDIS_CONTAINERS_SHUTDOWN_SIGNAL, REDIS_CONTAINERS_SOCKET

DEFAULT_TTL = 15 # seconds
SHUTDOWN_TTL = 120 # Seconds

@dataclass
class ContainerActive(DataClassJsonMixin):
    net_id: str
    socket_id: str

class ContainersModel:
    def __init__(self, redis: Redis):
        self.__r = redis

    def new_net_id(self) -> str:
        """
        Obtain a new net_id and increment the creating counter

        Returns:
        The new net_id as an hex encoded string
        """
        result = None
        with self.__r.pipeline() as pipe:
            pipe.multi()
            pipe.incr(REDIS_CONTAINERS_COUNT_KEY)
            pipe.incr(REDIS_CONTAINERS_COUNT_CREATING)
            result = pipe.execute()
        if result == None or result[0] == None:
            raise ValueError("Execpted result to not be null.")
        
        return hex(result[0])[2:]
    
    def request_net_id(self) -> str:
        """
        Obtain a net_id from the ready pool. This request is blocking for 2s
        and will timeout if no net_id is obtained by raising an exception.

        Returns:
        The net_id obtained
        """
        result = self.__r.blpop(REDIS_CONTAINERS_READY_QUEUE, timeout=2)
        if result == None:
            raise TimeoutError("Could not obtain a net_id after 2s")
        return result[1].decode("ascii")

    def ready(self, net_id: str, lazy: bool=False):
        """
        Mark a new net_id as ready for association. Lazy is for when it was
        reused and did not create it
        """
        with self.__r.pipeline() as pipe:
            pipe.multi()
            if not lazy:
                pipe.decr(REDIS_CONTAINERS_COUNT_CREATING)
            pipe.rpush(REDIS_CONTAINERS_READY_QUEUE, net_id)
            pipe.execute()
        

    def associate(self, socket_id: str, net_id: str):
        """
        Associate a net_id with a socket
        """
        container_active = ContainerActive(net_id=net_id, socket_id=socket_id)
        with self.__r.pipeline() as pipe:
            pipe.multi()
            pipe.sadd(REDIS_CONTAINERS_ACTIVE_SET, container_active.to_json())
            pipe.set(self.__key__socket(socket_id), net_id)
            pipe.set(self.__key__socket(socket_id, True), 1, ex=DEFAULT_TTL)
            pipe.execute()
    
    def touch(self, socket_id: str):
        """
        Update the TTL on the association so it's still valid
        """
        self.__r.set(self.__key__socket(socket_id, True), 1, ex=DEFAULT_TTL)

    def del_ttl(self, socket_id: str):
        """"
        Remove the TTL key if present
        """
        self.__r.delete(self.__key__socket(socket_id, True))

    def get_net_id(self, socket_id) -> str:
        """
        Returns the net_id from the socket_id
        """
        net_id = self.__r.get(self.__key__socket(socket_id))
        if net_id == None:
            return None

        return net_id.decode("ascii")

    def is_association_dead(self, socket_id: str) -> bool:
        """
        Check if the association is marked as dead
        """
        return not self.__r.exists(self.__key__socket(socket_id, True))

    def delete_association(self, socket_id: str, net_id: str) -> bool:
        """
        Remove the association that is linked to the socket_id

        Returns:
        True on success, else false
        """
        json = ContainerActive(net_id=net_id, socket_id=socket_id).to_json()
        with self.__r.pipeline() as pipe:
            pipe.multi()
            pipe.srem(REDIS_CONTAINERS_ACTIVE_SET, json)
            pipe.delete(self.__key__socket(socket_id))
            pipe.delete(self.__key__socket(socket_id, True))
            pipe.lrem(REDIS_CONTAINERS_READY_QUEUE, 0, net_id)
            pipe.execute()
        return True

    def get_associations(self) -> list[ContainerActive]:
        """
        Returns:
        A list of the active containers
        """
        members = self.__r.smembers(REDIS_CONTAINERS_ACTIVE_SET)
        associations = list()
        for member in members:
            container_active = ContainerActive.from_json(member.decode("ascii"))
            associations.append(container_active)
        
        return associations
    
    def queue_size(self) -> int:
        """
        Returns:
        The size of the ready queue + the creating containers
        """
        result = None
        with self.__r.pipeline() as pipe:
            pipe.multi()
            pipe.get(REDIS_CONTAINERS_COUNT_CREATING)
            pipe.llen(REDIS_CONTAINERS_READY_QUEUE)
            result = pipe.execute()
        
        if result == None:
            raise ValueError("Expected the result to not be null")
        if result[0] == None:
            result[0] = 0

        if result[1] == None:
            result[1] = 0
        
        return int(result[0]) + int(result[1])

    def get_ready(self) -> list[str]:
        """
        Returns:
        The list of net_id that are considered ready
        """
        members = self.__r.lrange(REDIS_CONTAINERS_READY_QUEUE, 0 , -1)
        list_str = list()
        for member in members:
            list_str.append(member.decode("ascii"))
        
        return list_str
    
    def is_shutdown(self) -> bool:
        """
        Returns:
        True if the system is in shutdown mode
        """
        return self.__r.exists(REDIS_CONTAINERS_SHUTDOWN_SIGNAL)

    def set_shutdown(self):
        """
        Sets the system in shutdown mode. DSR state will not launch any new tasks.
        """
        self.__r.set(REDIS_CONTAINERS_SHUTDOWN_SIGNAL, 1, ex=SHUTDOWN_TTL)

    def __key__socket(self, socket_id: str, ttl=False):
        if ttl:
            return REDIS_CONTAINERS_SOCKET + socket_id + ".ttl"
        else:
            return REDIS_CONTAINERS_SOCKET + socket_id
