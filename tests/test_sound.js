// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_sound.js   The hall ambience is built in the browser, so nothing here can be checked by
// loading a file: instead a stub Web Audio API runs the whole graph once. It catches the typos a tablet would
// otherwise find first — a node that does not exist, a parameter set the wrong way, a stop that never stops.
function param(){return{value:0,setValueAtTime(){},exponentialRampToValueAtTime(){},cancelScheduledValues(){},setTargetAtTime(){}};}
function node(extra){return Object.assign({connect(){},disconnect(){},start(){},stop(){}},extra);}
class AC{
  constructor(){this.sampleRate=48000;this.currentTime=0;this.state="running";this.destination=node();}
  resume(){}
  createGain(){return node({gain:param()});}
  createOscillator(){return node({frequency:param(),detune:param(),type:"sine"});}
  createBiquadFilter(){return node({frequency:param(),Q:param(),type:"bandpass"});}
  createBufferSource(){return node({buffer:null,loop:false});}
  createBuffer(ch,len){const d=new Float32Array(len);return{getChannelData:()=>d};}
}
let chimes=0;
global.window={AudioContext:AC,setInterval:(f)=>{chimes++;f();return 1;},clearInterval(){},setTimeout(){}};
require(require("path").join(__dirname, "..", "flightinfo", "static", "sound.js"));
const S=global.window.ZBSound;
S.setVolume(35);
if(!S.start()) throw new Error("start() refused");
if(!S.playing()) throw new Error("not playing after start");
if(chimes!==1) throw new Error("the chime timer was not armed");
S.setVolume(80);
S.stop();
if(S.playing()) throw new Error("still playing after stop");
if(!S.start()) throw new Error("it must be able to start again");
S.stop();
console.log("sound graph ok: builds, plays, changes volume, stops and restarts");
