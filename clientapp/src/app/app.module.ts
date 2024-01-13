import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { ClarityModule } from '@clr/angular';

import '@cds/core/icon/register.js';
import { ClarityIcons, snowflakeIcon, chatBubbleIcon, timesIcon} from '@cds/core/icon';
import { ChallengePageComponent } from './pages/challenge-page/challenge-page.component';
import { HelpPageComponent } from './pages/help-page/help-page.component';
import { NotfoundPageComponent } from './pages/notfound-page/notfound-page.component';
import { HomePageComponent } from './pages/home-page/home-page.component';
import { SocketIoConfig, SocketIoModule } from 'ngx-socket-io';
import { ReactiveFormsModule } from '@angular/forms';
import { isDevMode } from '@angular/core';

ClarityIcons.addIcons(chatBubbleIcon, snowflakeIcon, timesIcon)
const config: SocketIoConfig = { url: isDevMode() ? "http://localhost:5000" : window.location.origin, options: {}}

@NgModule({
  declarations: [
    AppComponent,
    ChallengePageComponent,
    HelpPageComponent,
    NotfoundPageComponent,
    HomePageComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    ClarityModule,
    SocketIoModule.forRoot(config),
    ReactiveFormsModule,
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
