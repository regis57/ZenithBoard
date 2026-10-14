// SPDX-License-Identifier: GPL-3.0-or-later
// The hall. A calm, continuous airport-concourse ambience, built here rather than played from a file: a few
// oscillators and one loop of noise, so there is no audio file in the repository and no licence to carry around.
// Nothing melodic is in front; after a minute the ear should be able to forget it. Every 80 seconds a soft
// three-note chime, the kind that precedes an announcement, but no announcement ever follows. The chime is
// written here and imitates no real airport's or railway's signature, which are somebody's work.
//
// Browsers refuse to start sound before someone has touched the page. That is the browser's rule, not a setting:
// the toggle button IS that touch, which is why the sound only ever starts from a tap and never on its own.
(function (w) {
  "use strict";

  var CHIME_EVERY_S = 80;         // first chime 80 s after the sound starts, then every 80 s
  var FADE_IN_S = 4;              // a wall that suddenly makes a noise is a fright: come up slowly
  var FADE_OUT_S = 1.2;

  var ctx = null, master = null, parts = [], timer = null, volume = 0.35, playing = false;

  function noiseBuffer(c) {       // four seconds of soft noise, looped: the ventilation and the distant rumble
    var n = c.sampleRate * 4, buf = c.createBuffer(1, n, c.sampleRate), d = buf.getChannelData(0), last = 0;
    for (var i = 0; i < n; i++) {
      var white = Math.random() * 2 - 1;
      last = (last + 0.02 * white) / 1.02;        // leaky integrator: takes the hiss off, leaves the rumble
      d[i] = last * 3.5;
    }
    return buf;
  }

  function drone(freq, detune, gain) {
    var o = ctx.createOscillator(), g = ctx.createGain(), lfo = ctx.createOscillator(), lg = ctx.createGain();
    o.type = "sine"; o.frequency.value = freq; o.detune.value = detune;
    g.gain.value = gain;
    lfo.frequency.value = 0.03 + Math.random() * 0.04;   // one slow breath every 15 to 30 seconds
    lg.gain.value = gain * 0.5;
    lfo.connect(lg); lg.connect(g.gain);
    o.connect(g); g.connect(master);
    o.start(); lfo.start();
    parts.push(o, lfo);
  }

  function bed() {
    // three low notes, slightly out of tune with each other, so the sound drifts instead of sitting still
    drone(55, -4, 0.22); drone(82.4, 6, 0.15); drone(110, -9, 0.10);
    var src = ctx.createBufferSource(), bp = ctx.createBiquadFilter(), g = ctx.createGain(),
        lfo = ctx.createOscillator(), lg = ctx.createGain();
    src.buffer = noiseBuffer(ctx); src.loop = true;
    bp.type = "bandpass"; bp.frequency.value = 420; bp.Q.value = 0.7;
    g.gain.value = 0.06;
    lfo.frequency.value = 0.016;                          // the rumble swells and falls over about a minute
    lg.gain.value = 0.03;
    lfo.connect(lg); lg.connect(g.gain);
    src.connect(bp); bp.connect(g); g.connect(master);
    src.start(); lfo.start();
    parts.push(src, lfo);
  }

  function chime() {
    // three notes, rising then settling, each a soft bell: a short attack and a long tail, well under the bed
    var notes = [783.99, 1046.50, 880.00], t0 = ctx.currentTime + 0.05;
    notes.forEach(function (f, i) {
      var t = t0 + i * 0.42, o = ctx.createOscillator(), g = ctx.createGain(), h = ctx.createOscillator(), hg = ctx.createGain();
      o.type = "sine"; o.frequency.value = f;
      h.type = "sine"; h.frequency.value = f * 2.01; hg.gain.value = 0.18;   // one overtone: a bell, not a beep
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(0.16, t + 0.03);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 2.6);
      h.connect(hg); hg.connect(g); o.connect(g); g.connect(master);
      o.start(t); h.start(t); o.stop(t + 2.8); h.stop(t + 2.8);
    });
  }

  function start() {
    if (playing) return true;
    try {
      var AC = w.AudioContext || w.webkitAudioContext;
      if (!AC) return false;                              // an old browser with no Web Audio: stay silent
      if (!ctx) ctx = new AC();
      if (ctx.state === "suspended") ctx.resume();
      master = ctx.createGain();
      master.gain.setValueAtTime(0.0001, ctx.currentTime);
      master.gain.exponentialRampToValueAtTime(Math.max(volume, 0.0002), ctx.currentTime + FADE_IN_S);
      master.connect(ctx.destination);
      bed();
      timer = w.setInterval(chime, CHIME_EVERY_S * 1000);
      playing = true;
      return true;
    } catch (e) {                                          // sound is a comfort, never a reason to break the wall
      playing = false;
      return false;
    }
  }

  function stop() {
    if (!playing) return;
    playing = false;
    if (timer) { w.clearInterval(timer); timer = null; }
    try {
      var end = ctx.currentTime + FADE_OUT_S;
      master.gain.cancelScheduledValues(ctx.currentTime);
      master.gain.setValueAtTime(master.gain.value || 0.0001, ctx.currentTime);
      master.gain.exponentialRampToValueAtTime(0.0001, end);
      parts.forEach(function (p) { try { p.stop(end + 0.05); } catch (e) { /* already stopped */ } });
      w.setTimeout(function () { try { master.disconnect(); } catch (e) { /* gone with the context */ } }, (FADE_OUT_S + 0.3) * 1000);
    } catch (e) { /* nothing playing to stop */ }
    parts = [];
  }

  w.ZBSound = {
    setVolume: function (pct) {
      volume = Math.max(0, Math.min(100, Number(pct) || 0)) / 100 * 0.7;   // 100 % is still a background, not a room filler
      if (playing && master) master.gain.setTargetAtTime(Math.max(volume, 0.0001), ctx.currentTime, 0.5);
    },
    start: start,
    stop: stop,
    playing: function () { return playing; }
  };
})(window);
