import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { CommonModule }   from '@angular/common';

import { AppComponent } from './app.component';
import { jqxTimelineModule } from 'jqwidgets-ng/jqxtimeline';

@NgModule({
  declarations: [
      AppComponent
  ],
  imports: [
    BrowserModule, CommonModule, jqxTimelineModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})

export class AppModule { }


