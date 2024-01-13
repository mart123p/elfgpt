import { Injectable } from '@angular/core';
import { Observer, Subject, Subscription } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LockService {

  private isLocked = false;
  private subject: Subject<boolean>;

  constructor() {
    this.subject = new Subject();
  }


  setLock(): void{
    if(!this.isLocked){
      this.isLocked = true;
      //Broadcast
      this.subject.next(this.isLocked);
      document.querySelector("body")?.classList.add("pointer-wait");

      window.onbeforeunload = (event) => {
        const confirmationMessage = "Processing is in progress, are you sure you want to leave ?";
        if(this.isLocked){
          event.preventDefault();
          event.returnValue = confirmationMessage;
          return confirmationMessage;
        }
  
        return "";
      }
    }
  }

  clearLock(): void{
    if(this.isLocked){
      this.isLocked = false;

      //Broadcast
      this.subject.next(this.isLocked);
      document.querySelector("body")?.classList.remove("pointer-wait");
      window.onbeforeunload = () => {};
    }
  }

  subscribe(observerOrNext?: Partial<Observer<boolean>> | ((value: boolean) => void)): Subscription {
    return this.subject.subscribe(observerOrNext);
  }

}
