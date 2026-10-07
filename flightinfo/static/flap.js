// SPDX-License-Identifier: GPL-3.0-or-later
// Split-flap ("Frankfurt departure board") model: a grid of character cells. When a cell's target letter changes it
// does not jump: it flips through the alphabet one flap at a time until it reaches the new letter, rows start one after
// the other and letters one after the other inside a row, like the old mechanical boards. No DOM here, so it can be
// tested with node; app.js draws it.
(function (root) {
  "use strict";
  var CHARS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,-/:+()→";
  var STEP_MS = 38;        // one flap falls
  var ROW_MS = 140;        // delay between one row starting and the next
  var COL_MS = 16;         // delay between one letter starting and the next, inside a row

  function norm(ch) { ch = String(ch).toUpperCase(); return CHARS.indexOf(ch) >= 0 ? ch : " "; }
  function stepsBetween(a, b) { var i = CHARS.indexOf(norm(a)), j = CHARS.indexOf(norm(b)); return (j - i + CHARS.length) % CHARS.length; }

  function Board(cols, rows, rand) {
    this.cols = cols; this.rows = rows; this.rand = rand || Math.random;
    this.cells = [];
    for (var i = 0; i < cols * rows; i++) this.cells.push({ ch: " ", tgt: " ", t0: 0, n: 0 });
  }

  // texts: one string per row (left-aligned, padded or cut to `cols`). instant: no flipping (first screen, reduced motion).
  Board.prototype.setRows = function (texts, now, instant) {
    for (var r = 0; r < this.rows; r++) {
      var line = String(texts[r] == null ? "" : texts[r]);
      for (var c = 0; c < this.cols; c++) {
        var cell = this.cells[r * this.cols + c], want = norm(c < line.length ? line[c] : " ");
        if (want === cell.tgt) continue;
        var cur = this.shown(cell, now).next;                  // where the flaps are right now (a flip may be under way)
        cell.ch = cur; cell.tgt = want;
        cell.n = stepsBetween(cur, want);
        if (instant || !cell.n) { cell.ch = want; cell.n = 0; continue; }
        cell.t0 = now + r * ROW_MS + c * COL_MS + this.rand() * 24;
      }
    }
  };

  // What one cell shows at time `now`: {prev, next, phase, flipping}. Flipping cells go prev -> next with phase 0..1.
  Board.prototype.shown = function (cell, now) {
    if (cell.ch === cell.tgt) return { prev: cell.ch, next: cell.ch, phase: 0, flipping: false };
    var el = now - cell.t0;
    if (el < 0) return { prev: cell.ch, next: cell.ch, phase: 0, flipping: false };            // waiting for its turn
    var k = Math.floor(el / STEP_MS), i = CHARS.indexOf(cell.ch);
    if (k >= cell.n) return { prev: cell.tgt, next: cell.tgt, phase: 0, flipping: false };    // arrived
    return { prev: CHARS[(i + k) % CHARS.length], next: CHARS[(i + k + 1) % CHARS.length], phase: (el % STEP_MS) / STEP_MS, flipping: true };
  };

  Board.prototype.cell = function (r, c, now) { return this.shown(this.cells[r * this.cols + c], now); };

  // Settle finished cells; true while anything is still waiting or flipping (the caller keeps animating).
  Board.prototype.update = function (now) {
    var busy = false;
    for (var i = 0; i < this.cells.length; i++) {
      var cell = this.cells[i];
      if (cell.ch === cell.tgt) continue;
      if (now - cell.t0 >= cell.n * STEP_MS) { cell.ch = cell.tgt; cell.n = 0; } else busy = true;
    }
    return busy;
  };

  Board.prototype.text = function (now) {                    // the letters currently shown, one string per row (for tests)
    var out = [];
    for (var r = 0; r < this.rows; r++) { var s = ""; for (var c = 0; c < this.cols; c++) s += this.cell(r, c, now).prev; out.push(s); }
    return out;
  };

  var api = { Board: Board, CHARS: CHARS, STEP_MS: STEP_MS, ROW_MS: ROW_MS, COL_MS: COL_MS, norm: norm, stepsBetween: stepsBetween };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FlapKit = api;
})(typeof self !== "undefined" ? self : this);
