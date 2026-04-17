#!/usr/bin/env python3
"""
Discord Countdown Timer
=======================
Speaks each second using Windows text-to-speech (no beeps).

How to use with Discord
-----------------------
1. Download VB-Audio Virtual Cable (free): https://vb-audio.com/Cable/
2. In Windows Sound settings set default PLAYBACK device to
   "CABLE Input (VB-Audio Virtual Cable)"
3. In Discord > Settings > Voice & Video set Input Device to
   "CABLE Output (VB-Audio Virtual Cable)"
4. Run this script.  People in your voice channel will hear the countdown.

Requirements
------------
    pip install pyttsx3
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import time

# ─── Discord dark colour palette ─────────────────────────────────────────────
BG     = '#2C2F33'
DARK   = '#23272A'
FG     = '#FFFFFF'
ACCENT = '#7289DA'
GREEN  = '#43B581'
YELLOW = '#FAA61A'
RED    = '#F04747'
GRAY   = '#72767D'

# ─── Number → spoken words (0 – 3 599 s) ────────────────────────────────────
_ONES = [
    '', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',
    'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen',
    'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen',
]
_DIGITS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
_TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty',
         'sixty', 'seventy', 'eighty', 'ninety']


def secs_to_words(n: int) -> str:
    """Return spoken English for n as a plain number (0–5999)."""
    if n == 0:
        return 'zero'
    if n < 20:
        return _ONES[n]
    if n < 100:
        t, o = divmod(n, 10)
        # Faster two-digit callout style (e.g. 22 -> "two two") helps keep speech < 1 second.
        return _DIGITS[t] if o == 0 else f'{_DIGITS[t]} {_DIGITS[o]}'
    if n < 1000:
        h, r = divmod(n, 100)
        return _ONES[h] + ' hundred' + (f' {secs_to_words(r)}' if r else '')
    th, r = divmod(n, 1000)
    return secs_to_words(th) + ' thousand' + (f' {secs_to_words(r)}' if r else '')


# ─── Dedicated TTS worker thread ─────────────────────────────────────────────
class _TTSThread(threading.Thread):
    """
    Owns a single pyttsx3 engine.  Callers push
        (text, volume, voice_id, done_event)
    onto the queue; done_event is set when the utterance finishes.
    Push None to shut down.
    """

    def __init__(self):
        super().__init__(daemon=True, name='tts-worker')
        self._q      = queue.Queue()
        self._ready  = threading.Event()
        self.voices  = []
        self.error   = None

    def run(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', 175)
            all_voices   = self._engine.getProperty('voices')
            self.voices  = all_voices
            self._best_voice_id = self._pick_best(all_voices)
            if self._best_voice_id:
                self._engine.setProperty('voice', self._best_voice_id)
        except Exception as exc:
            self.error = exc
        finally:
            self._ready.set()

        if self.error:
            return

        while True:
            item = self._q.get()
            if item is None:
                break
            text, volume, voice_id, done = item
            try:
                # Use explicit override only if one was passed
                vid = voice_id or self._best_voice_id
                if vid:
                    self._engine.setProperty('voice', vid)
                self._engine.setProperty('volume', max(0.0, min(1.0, volume)))
                self._engine.say(text)
                self._engine.runAndWait()
            finally:
                done.set()

    @staticmethod
    def _pick_best(voices):
        """Return the id of the most natural-sounding available voice."""
        import re
        priority = [
            r'zira',          # Microsoft Zira (clear US female)
            r'aria',          # Microsoft Aria (neural)
            r'jenny',         # Microsoft Jenny
            r'guy',           # Microsoft Guy
            r'davis',         # Microsoft Davis
            r'steffan',       # Microsoft Steffan
            r'david',         # Microsoft David (classic, decent)
            r'hazel',         # Microsoft Hazel (UK)
            r'susan',
            r'mark',
        ]
        for pat in priority:
            for v in voices:
                if re.search(pat, v.name, re.I):
                    return v.id
        return voices[0].id if voices else ''

    def speak_sync(self, text: str, volume: float, voice_id: str = ''):
        """Queue text and block until it has been spoken."""
        if self.error:
            return
        evt = threading.Event()
        self._q.put((text, volume, voice_id, evt))
        evt.wait()

    def shutdown(self):
        self._q.put(None)


# ─── Main application ─────────────────────────────────────────────────────────
class CountdownTimer:

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title('Discord Countdown Timer')
        root.configure(bg=BG)
        root.resizable(False, False)
        root.protocol('WM_DELETE_WINDOW', self._on_close)

        self._running    = False
        self._paused     = False
        self._remaining  = 0
        self._voice_ids  = []
        self._flash_on   = False
        self._flash_id   = None

        self._tts = _TTSThread()
        self._tts.start()

        self._build_ui()
        root.after(100, self._check_tts_ready)

    # ── TTS ready-check (polled from main thread) ─────────────────────────────
    def _check_tts_ready(self):
        if not self._tts._ready.is_set():
            self.root.after(100, self._check_tts_ready)
            return
        if self._tts.error:
            messagebox.showerror(
                'TTS Error',
                f'Text-to-speech failed to start:\n{self._tts.error}\n\n'
                'Install with:  pip install pyttsx3')
            self.root.after(200, self.root.destroy)
            return
        names = [v.name for v in self._tts.voices]
        self._voice_ids = [v.id   for v in self._tts.voices]
        self._voice_cb['values'] = names
        # Pre-select the auto-picked best voice in the dropdown
        best_id = self._tts._best_voice_id
        try:
            best_idx = self._voice_ids.index(best_id)
        except ValueError:
            best_idx = 0
        if names:
            self._voice_cb.current(best_idx)
        self._voice_label.config(
            text=f'\u2713 {names[best_idx]}' if names else 'Default')

    # ── UI helpers ────────────────────────────────────────────────────────────
    def _lbl(self, parent, text='', fg=FG, bg=BG, font=None, **kw):
        return tk.Label(parent, text=text, fg=fg, bg=bg,
                        font=font or ('Segoe UI', 10), **kw)

    def _mkbtn(self, parent, text, color, cmd, state='normal'):
        return tk.Button(
            parent, text=text, command=cmd,
            bg=color, fg=FG, activeforeground=FG, activebackground=color,
            font=('Segoe UI', 13, 'bold'),
            width=8, relief='flat', padx=8, pady=6,
            state=state, cursor='hand2')

    def _rbtn(self, parent, text, var, value):
        return tk.Radiobutton(
            parent, text=text, variable=var, value=value,
            bg=DARK, fg=FG, selectcolor=ACCENT,
            activebackground=DARK, font=('Segoe UI', 9))

    def _spinbox(self, parent, var, lo, hi):
        return tk.Spinbox(
            parent, from_=lo, to=hi, width=3, textvariable=var,
            font=('Segoe UI', 13), bg=BG, fg=FG,
            buttonbackground=DARK, relief='flat', bd=3)

    # ── Build the full UI ─────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=DARK, pady=10)
        hdr.pack(fill='x')
        self._lbl(hdr, 'Discord Countdown Timer',
                  fg=ACCENT, bg=DARK,
                  font=('Segoe UI', 16, 'bold')).pack()

        # Large clock
        cf = tk.Frame(self.root, bg=BG, pady=16)
        cf.pack(fill='x')
        self._clock_var  = tk.StringVar(value='00:00')
        self._status_var = tk.StringVar(value='Ready')
        tk.Label(cf, textvariable=self._clock_var,
                 font=('Segoe UI', 72, 'bold'), fg=FG, bg=BG).pack()
        self._lbl(cf, textvariable=self._status_var,
                  fg=GRAY, font=('Segoe UI', 11)).pack()

        # Settings card
        card = tk.Frame(self.root, bg=DARK, padx=20, pady=12)
        card.pack(fill='x', padx=14, pady=(0, 8))

        def rlbl(text, row):
            self._lbl(card, text, bg=DARK, fg=GRAY,
                      font=('Segoe UI', 9)).grid(
                      row=row, column=0, sticky='w', padx=(0, 14), pady=3)

        # Duration
        rlbl('Duration', 0)
        df = tk.Frame(card, bg=DARK)
        df.grid(row=0, column=1, sticky='w')
        self._min_var = tk.StringVar(value='1')
        self._sec_var = tk.StringVar(value='0')
        self._spinbox(df, self._min_var, 0, 99).pack(side='left')
        self._lbl(df, ' m  ', bg=DARK, fg=FG,
                  font=('Segoe UI', 13)).pack(side='left')
        self._spinbox(df, self._sec_var, 0, 59).pack(side='left')
        self._lbl(df, ' s', bg=DARK, fg=FG,
                  font=('Segoe UI', 13)).pack(side='left')

        # Volume
        rlbl('Volume', 1)
        vf = tk.Frame(card, bg=DARK)
        vf.grid(row=1, column=1, sticky='w', pady=6)
        self._vol_var = tk.IntVar(value=80)
        self._vol_pct = tk.StringVar(value='80%')
        ttk.Scale(vf, from_=0, to=100, variable=self._vol_var,
                  orient='horizontal', length=170,
                  command=lambda v: self._vol_pct.set(
                      f'{int(float(v))}%')).pack(side='left')
        self._lbl(vf, '', bg=DARK, fg=FG, font=('Segoe UI', 10),
                  textvariable=self._vol_pct, width=5).pack(side='left', padx=5)

        # Announce interval
        rlbl('Announce every', 2)
        af = tk.Frame(card, bg=DARK)
        af.grid(row=2, column=1, sticky='w')
        self._interval_var = tk.IntVar(value=1)
        for v, t in [(1, '1 s'), (5, '5 s'), (10, '10 s'), (30, '30 s')]:
            self._rbtn(af, t, self._interval_var, v).pack(side='left', padx=3)

        # Final-N-seconds threshold
        rlbl('Count every second for last', 3)
        ff = tk.Frame(card, bg=DARK)
        ff.grid(row=3, column=1, sticky='w', pady=3)
        self._final_var = tk.IntVar(value=10)
        for v, t in [(5, '5 s'), (10, '10 s'), (30, '30 s'), (60, '60 s')]:
            self._rbtn(ff, t, self._final_var, v).pack(side='left', padx=3)

        # Flash threshold
        rlbl('Flash screen at last', 4)
        flf = tk.Frame(card, bg=DARK)
        flf.grid(row=4, column=1, sticky='w', pady=3)
        self._flash_var = tk.IntVar(value=0)
        self._flash_slider = ttk.Scale(
            flf, from_=0, to=90, variable=self._flash_var,
            orient='horizontal', length=160,
            command=lambda v: self._flash_var.set(int(float(v))))
        self._flash_slider.pack(side='left')
        vcmd = card.register(lambda P: P == '' or (P.isdigit() and 0 <= int(P) <= 90))
        self._flash_entry = tk.Entry(
            flf, textvariable=self._flash_var, width=4,
            validate='key', validatecommand=(vcmd, '%P'),
            font=('Segoe UI', 11), bg=BG, fg=FG,
            insertbackground=FG, relief='flat', bd=3)
        self._flash_entry.pack(side='left', padx=(6, 2))
        self._lbl(flf, 's  (0 = off)', bg=DARK, fg=GRAY,
                  font=('Segoe UI', 9)).pack(side='left')

        # Voice
        rlbl('Voice', 5)
        vof = tk.Frame(card, bg=DARK)
        vof.grid(row=5, column=1, sticky='w', pady=4)
        self._voice_label = self._lbl(vof, 'Detecting…', bg=DARK,
                                      fg=GREEN, font=('Segoe UI', 9))
        self._voice_label.pack(anchor='w')
        self._voice_var = tk.StringVar()
        self._voice_cb  = ttk.Combobox(vof, textvariable=self._voice_var,
                                        width=34, state='readonly')
        self._voice_cb.pack(anchor='w', pady=(4, 0))

        # Buttons
        bf = tk.Frame(self.root, bg=BG, pady=12)
        bf.pack()
        self._start_btn = self._mkbtn(bf, 'START', GREEN,  self.start)
        self._start_btn.grid(row=0, column=0, padx=5)
        self._pause_btn = self._mkbtn(bf, 'PAUSE', YELLOW, self.pause_resume,
                                      state='disabled')
        self._pause_btn.grid(row=0, column=1, padx=5)
        self._stop_btn  = self._mkbtn(bf, 'STOP',  RED,    self.stop,
                                      state='disabled')
        self._stop_btn.grid(row=0, column=2, padx=5)

        # Footer hint
        foot = tk.Frame(self.root, bg=DARK, pady=6)
        foot.pack(fill='x')
        self._lbl(
            foot,
            'To use in Discord: set Windows playback device to '
            '"CABLE Input (VB-Audio)"\nthen select '
            '"CABLE Output (VB-Audio)" as your Discord mic.',
            bg=DARK, fg=GRAY, font=('Segoe UI', 8),
            justify='center').pack()

    # ── Controls ──────────────────────────────────────────────────────────────
    def start(self):
        dur = self._get_duration()
        if dur <= 0:
            messagebox.showwarning('Invalid duration',
                                   'Please set a duration greater than 0.')
            return
        self._running   = True
        self._paused    = False
        self._remaining = dur
        self._start_btn.config(state='disabled')
        self._pause_btn.config(state='normal', text='PAUSE')
        self._stop_btn .config(state='normal')
        self._status_var.set('Running…')
        threading.Thread(target=self._worker, daemon=True).start()

    def pause_resume(self):
        if self._paused:
            self._paused = False
            self._pause_btn.config(text='PAUSE')
            self._status_var.set('Running…')
        else:
            self._paused = True
            self._pause_btn.config(text='RESUME')
            self._status_var.set('Paused')

    def stop(self):
        self._running = False
        self._paused  = False
        self.root.after(0, self._set_clock, 0)
        self.root.after(0, self._stop_flash)
        self._status_var.set('Stopped')
        self._reset_btns()

    def _reset_btns(self):
        self._start_btn.config(state='normal')
        self._pause_btn.config(state='disabled', text='PAUSE')
        self._stop_btn .config(state='disabled')

    # ── Screen flash ──────────────────────────────────────────────────────────
    def _start_flash(self):
        if self._flash_id is not None:
            return  # already running
        self._flash_on = False
        self._do_flash()

    def _do_flash(self):
        if self._flash_id is not None and not self._running:
            self._stop_flash()
            return
        self._flash_on = not self._flash_on
        colour = '#6b0000' if self._flash_on else BG
        self.root.configure(bg=colour)
        # also update all direct child frames so the whole window changes
        for w in self.root.winfo_children():
            try:
                w.configure(bg=colour if w.cget('bg') in (BG, '#6b0000') else w.cget('bg'))
            except Exception:
                pass
        self._flash_id = self.root.after(500, self._do_flash)

    def _stop_flash(self):
        if self._flash_id is not None:
            self.root.after_cancel(self._flash_id)
            self._flash_id = None
        self._flash_on = False
        self.root.configure(bg=BG)
        for w in self.root.winfo_children():
            try:
                if w.cget('bg') == '#6b0000':
                    w.configure(bg=BG)
            except Exception:
                pass

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_duration(self) -> int:
        try:
            m = max(0, int(self._min_var.get()))
            s = max(0, min(59, int(self._sec_var.get())))
            return m * 60 + s
        except ValueError:
            return 0

    def _set_clock(self, seconds: int):
        m, s = divmod(seconds, 60)
        self._clock_var.set(f'{m:02d}:{s:02d}')

    def _get_volume(self) -> float:
        return self._vol_var.get() / 100.0

    def _get_voice_id(self) -> str:
        idx = self._voice_cb.current()
        if 0 <= idx < len(self._voice_ids):
            return self._voice_ids[idx]
        return ''

    # ── Countdown worker (background thread) ──────────────────────────────────
    def _worker(self):
        interval = self._interval_var.get()
        final    = self._final_var.get()
        total    = self._remaining
        voice_id = self._get_voice_id()

        def say(text: str):
            if self._running:
                self._tts.speak_sync(text, self._get_volume(), voice_id)

        for count in range(total, 0, -1):
            if not self._running:
                return

            # Spin while paused
            while self._paused and self._running:
                time.sleep(0.05)
            if not self._running:
                return

            tick = time.monotonic()
            self.root.after(0, self._set_clock, count)

            # Start flash if threshold reached
            flash_at = self._flash_var.get()
            if flash_at > 0 and count <= flash_at and self._flash_id is None:
                self.root.after(0, self._start_flash)

            # Speak when count falls within interval or final zone
            if (count <= final) or (count % interval == 0):
                say(secs_to_words(count))

            # Sleep the remaining portion of this second
            spent = time.monotonic() - tick
            time.sleep(max(0.0, 1.0 - spent))
            self._remaining = count - 1

        if self._running:
            self.root.after(0, self._set_clock, 0)
            say("Time's up!")
            self.root.after(0, self._on_complete)

    def _on_complete(self):
        self._running = False
        self._stop_flash()
        self._status_var.set("Done! \u2705")
        self._reset_btns()

    # ── Clean exit ────────────────────────────────────────────────────────────
    def _on_close(self):
        self._running = False
        self._tts.shutdown()
        self.root.destroy()


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    CountdownTimer(root)
    root.mainloop()
