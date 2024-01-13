from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin

EVENT_HEARTBEAT = "ping"

EVENT_CAPACITY_REQUEST = "capacity_request"
EVENT_CAPACITY_RESPONSE = "capacity_response"

ROOM_CAPACITY_BROADCAST = "capacity"

EVENT_CANCEL_REQUEST = "cancel_request"
EVENT_CANCEL_RESPONSE = "cancel_response"

EVENT_MESSAGE_REQUEST = "message_request"
EVENT_MESSAGE_RESPONSE = "message_response"

EVENT_SERVER_ERROR = "server_error"

@dataclass
class CapacityRequest(DataClassJsonMixin):
    challenge_id: int

@dataclass
class CapacityResponse(DataClassJsonMixin):
    queue_size: int
    diff: int
    ready: bool

@dataclass
class MessageRequest(DataClassJsonMixin):
    challenge_id: int
    content: str

@dataclass
class MessageResponse(DataClassJsonMixin):
    content: str
    clawback: bool
    stop: bool

@dataclass
class ServerErrorResponse(DataClassJsonMixin):
    error_msg: str