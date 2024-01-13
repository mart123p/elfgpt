import { Injectable } from '@angular/core';
import { Socket } from 'ngx-socket-io';
import { Observable } from 'rxjs';
import { CapacityResponse, EVENT_CANCEL_RESPONSE, EVENT_CAPACITY_RESPONSE,
  EVENT_HEARTBEAT, EVENT_MESSAGE_RESPONSE, EVENT_SERVER_ERROR, MessageResponse, ServerErrorResponse } from '../dtos';


const HEARTBEAT_TIME_MS = 10000;

@Injectable({
  providedIn: 'root'
})
export class SocketService {
  private connect!: Observable<undefined>;
  private disconnect!: Observable<undefined>;
  private cancel!: Observable<undefined>;

  private serverError!: Observable<ServerErrorResponse>;
  private capacity!: Observable<CapacityResponse>;
  private message!: Observable<MessageResponse>;


  private interval: number | undefined = undefined;
  constructor(private socket: Socket) { 
    this.setup();
  }

  sendMessage(event: string, msg: any) {
    if(msg === undefined){
      this.socket.emit(event);
    }else{
      this.socket.emit(event, JSON.stringify(msg));
    }
  }

  getConnect(): Observable<undefined> {
    return this.connect;
  }

  getDisconnect(): Observable<undefined> {
    return this.disconnect;
  }

  getServerError(): Observable<ServerErrorResponse>{
    return this.serverError;
  }


  getMessageResponse(): Observable<MessageResponse>{
    return this.message;
  }
  
  getCapacityResponse(): Observable<CapacityResponse>{
    return this.capacity;
  }

  getCancelResponse(): Observable<undefined>{
    return this.cancel;
  }


  private setup(): void {
    this.socket.on("connect", () => {
      this.interval = window.setInterval(() => {
        this.socket.emit(EVENT_HEARTBEAT)
      }, HEARTBEAT_TIME_MS);
    });

    this.socket.on("disconnect", () => {
      if(this.interval !== undefined){
        clearInterval(this.interval);
      }
    });

    this.connect = new Observable((subscriber) => {
      this.socket.on("connect", () => {
        subscriber.next();
      });
    })

    this.disconnect = new Observable((subscriber) => {
      this.socket.on("disconnect", () => {
        subscriber.next();
      });
    });

    this.serverError = new Observable((subscriber) => {
      this.socket.on(EVENT_SERVER_ERROR, (payload: string)=> {
        subscriber.next(JSON.parse(payload));
      });
    });

    this.message = new Observable((subscriber) =>{
      this.socket.on(EVENT_MESSAGE_RESPONSE, (payload: string) => {
        subscriber.next(JSON.parse(payload));
      });
    });

    this.capacity = new Observable((subscriber) => {
      this.socket.on(EVENT_CAPACITY_RESPONSE, (payload: string) => {
        subscriber.next(JSON.parse(payload));
      });
    });

    this.cancel = new Observable((subscriber) => {
      this.socket.on(EVENT_CANCEL_RESPONSE, () => {
        subscriber.next();
      });
    });
  }
}
