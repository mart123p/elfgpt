import { Component, OnInit } from '@angular/core';
import { FormControl } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { challenges } from 'src/app/challenges';
import { CapacityRequest, EVENT_CANCEL_REQUEST, EVENT_CAPACITY_REQUEST, EVENT_MESSAGE_REQUEST, MessageRequest } from 'src/app/dtos';
import { LockService } from 'src/app/services/lock.service';
import { SocketService } from 'src/app/services/socket.service';

enum ChallengeState{
  DONE,
  CAPACITY_REQUEST,
  CAPACITY_WAIT,
  GENERATING
}

@Component({
  selector: 'app-challenge-page',
  templateUrl: './challenge-page.component.html',
  styleUrls: ['./challenge-page.component.css']
})
export class ChallengePageComponent implements OnInit{

  id: number = 0;
  description: string = "";
  type: string = "";
  logo: string = "";

  state: ChallengeState = ChallengeState.DONE;
  stateEnum = ChallengeState;
  queuePos: number = 0;
  
  llmMessage = "";
  userMessage = new FormControl();
  isCanceling = false;
  locked = false;

  private queueSize = 0;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private socket: SocketService,
    private lock: LockService){

  }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      const idStr = params['id']
      if(idStr == null){
        this.router.navigateByUrl("/404");
        return;
      }

      this.id = parseInt(idStr);

      if(Number.isNaN(this.id)){
        this.router.navigateByUrl("/404");
        return;
      }
      const challenge = challenges.find(x => x.id == this.id);
      if(challenge == undefined){
        this.router.navigateByUrl("/404");
        return;
      }

      this.description = challenge.description;
      this.type = challenge.type;
      this.logo = challenge.logo;

      //Set variables to default
      this.llmMessage = "";
      this.userMessage = new FormControl();
      this.queuePos = 0;
      this.queueSize = 0;
      this.isCanceling = false;
      this.locked = false;
      this.state = ChallengeState.DONE;
      
    });

    this.socket.getCapacityResponse().subscribe((capacityResponse)=>{
      if(this.state === ChallengeState.CAPACITY_REQUEST) {
        this.queueSize = capacityResponse.queue_size;
        this.queuePos = this.queueSize;
        this.state = ChallengeState.CAPACITY_WAIT;
      }else if(this.state === ChallengeState.CAPACITY_WAIT){
        this.queuePos += capacityResponse.diff;
        
        if(this.queuePos < 0){
          this.queuePos = 0;
        }
      }
      
      if(capacityResponse.ready){
        //We are ready to receive the message
        this.sendMessage();
      }
    });

    this.socket.getMessageResponse().subscribe((messageResponse) => {
      if(messageResponse.clawback){
        this.llmMessage = messageResponse.content;
      }else{
        this.llmMessage += messageResponse.content;
      }

      if(messageResponse.stop){
        this.state = ChallengeState.DONE;
        this.lock.clearLock();
      }
    });

    this.socket.getCancelResponse().subscribe(() => {
      this.lock.clearLock();
      this.state = ChallengeState.DONE;
      this.isCanceling = false;
    });

    this.lock.subscribe((lockState) => {
      this.locked = lockState;
      if(this.locked){
        this.userMessage.disable();
      }else{
        this.userMessage.enable();
      }
    });

  }

  requestCapacity(): void {
    this.llmMessage = "";
    this.state = ChallengeState.CAPACITY_REQUEST;
    const payload: CapacityRequest = {
      challenge_id: this.id
    }
    this.socket.sendMessage(EVENT_CAPACITY_REQUEST, payload);
    this.lock.setLock();
  }

  cancel(): void{
    this.socket.sendMessage(EVENT_CANCEL_REQUEST, undefined);
    this.isCanceling = true;
  }

  private sendMessage(): void {
    //We need to send the message
    const payload: MessageRequest = {
      challenge_id: this.id,
      content: this.userMessage.value
    };

    this.socket.sendMessage(EVENT_MESSAGE_REQUEST, payload);
    this.state = ChallengeState.GENERATING;
  }
}
