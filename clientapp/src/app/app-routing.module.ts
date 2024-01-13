import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ChallengePageComponent } from './pages/challenge-page/challenge-page.component';
import { HelpPageComponent } from './pages/help-page/help-page.component';
import { NotfoundPageComponent } from './pages/notfound-page/notfound-page.component';
import { HomePageComponent } from './pages/home-page/home-page.component';

const routes: Routes = [
  {path: "challenge/:id", component: ChallengePageComponent },
  {path: "disclaimer", component: HelpPageComponent},
  {path: "", component: HomePageComponent},
  {path: "**", component: NotfoundPageComponent},
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
