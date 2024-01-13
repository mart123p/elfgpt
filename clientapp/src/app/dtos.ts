//Request capacity
export const EVENT_CAPACITY_REQUEST="capacity_request";
export interface CapacityRequest{
    challenge_id: number;
}

export const EVENT_HEARTBEAT="ping";

export const EVENT_CAPACITY_RESPONSE="capacity_response";
export interface CapacityResponse{
    queue_size: number; //Size of the queue initially
    diff: number; //Difference to apply to the size of the queue
    ready: boolean; //Indicates that the user can request
}

//Cancel capacity request or message request
export const EVENT_CANCEL_REQUEST="cancel_request";

//Server confirms that the request was cancelled properly.
export const EVENT_CANCEL_RESPONSE="cancel_response";

//Once on position 0 for capacityResponse client has 5s to send a message request
//before being assigned to another client.
export const EVENT_MESSAGE_REQUEST="message_request";
export interface MessageRequest{
    challenge_id: number;
    content: string;
}

//Output from the LLM to the client
export const EVENT_MESSAGE_RESPONSE="message_response";
export interface MessageResponse{
    content: string;
    clawback: boolean; //Indicates to the client to remove all the previous text
    stop: boolean; //Indicates that this is the final message
}

//Ways for the server to send errors to the client
export const EVENT_SERVER_ERROR="server_error";
export interface ServerErrorResponse{
    error_msg: string;
}