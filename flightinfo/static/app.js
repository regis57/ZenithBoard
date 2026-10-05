let p=[],i=0;
async function f(){try{let r=await fetch(`/api/planes?radius=${document.getElementById('radiusInput').value}`),d=await r.json();if(d.planes)p=d.planes;}catch(e){}}
function u(){
let n=document.getElementById('no-flights'),d=document.getElementById('flight-data'),ph=document.getElementById('flight-photo');
if(!p.length){n.classList.remove('hidden');d.classList.add('hidden');ph.style.display='none';return;}
n.classList.add('hidden');d.classList.remove('hidden');if(i>=p.length)i=0;let x=p[i];
document.getElementById('flight-callsign').innerText=x.flight||"UNKNOWN";
document.getElementById('flight-hex').innerText=`[${x.hex.toUpperCase()}] ${x.distance_km}km`;
document.getElementById('flight-speed').innerText=x.speed_kmh?x.speed_kmh:'---';
document.getElementById('flight-alt').innerText=x.alt_baro!=="ground"?x.alt_baro:'GND';
document.getElementById('flight-track').innerText=x.track?`${Math.round(x.track)}°`:'---°';
document.getElementById('flight-vspeed').innerText=x.v_speed!==null?x.v_speed:'---';
if(x.photo){ph.src=x.photo;ph.style.display='block';}else{ph.style.display='none';}i++;}
f();u();setInterval(f,1000);setInterval(u,5000);