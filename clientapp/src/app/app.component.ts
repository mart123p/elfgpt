import { Component, OnInit } from '@angular/core';

import { challenges } from "./challenges";
import { SocketService } from './services/socket.service';
import { LockService } from './services/lock.service';


export enum ConnectionState {
  CONNECTING,
  OK,
  DISCONNECTED,
  TIMEOUT
}


@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit{
  CHALLENGES = challenges;
  hasServerError = false;
  serverErrorMsg = "";
  locked = true;
  loading = true;

  state = ConnectionState.CONNECTING;
  stateEnum = ConnectionState;

  constructor(
    private socket: SocketService,
    private lock: LockService){

  }

  ngOnInit(): void {
    this.socket.getConnect().subscribe(() =>{
      this.state = ConnectionState.OK;
      this.locked = false;
      this.loading = false;
    })

    this.socket.getDisconnect().subscribe(() => {
      this.state = ConnectionState.DISCONNECTED;
    })

    setTimeout(() => {
      if(this.state === ConnectionState.CONNECTING){
        this.state = ConnectionState.TIMEOUT;
      }
    }, 5000);

    this.socket.getServerError().subscribe((serverError) => {
      this.hasServerError = true;
      this.serverErrorMsg = serverError.error_msg;

      console.error(`Server encountered an error: ${serverError.error_msg}}`)
    });

    this.lock.subscribe((lockState) => {
      this.locked = lockState;
    })
  }

  refreshPage(): void {
    location.reload();
  }

  serverErrorDismiss(): void{
    this.hasServerError = false;
  }
}
