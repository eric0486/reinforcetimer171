Discord Countdown Timer - Quick Guide
====================================

Files in this folder
--------------------
- countdown_timer.html   (recommended: easiest, no Python needed)
- countdown_timer.py     (Python app version)
- run.bat                (starts Python version after dependency check)
- requirements.txt       (Python dependency list)


1) Fastest way to use (HTML version)
------------------------------------
1. Open countdown_timer.html in Edge or Firefox.
2. Set duration (minutes + seconds).
3. Set volume and speech rate.
4. Choose voice mode:
   - Google TTS Voice (Cloud): internet required.
   - Local Microsoft/System Voice: uses voices installed on your PC.
5. Optional: click TEST VOICE to verify sound.
6. Click START.

Notes:
- Flash screen can be set from 0 to 90 seconds (0 = off).
- Countdown speaks number names each interval (for example: "ninety", "eighty nine", etc.).
- New option: KvK Auto Rally mode.
  - Set your own march time to target.
  - Add one or more enemy rallies (enemy march time + rally time left).
  - The timer automatically picks the rally that lands the soonest.
  - It counts down to your required send time and gives an audible alert 10 seconds before send.


2) Python version (optional)
----------------------------
Use this if you prefer the desktop app.

Install:
1. Install Python 3.
2. Open terminal in this folder.
3. Run: pip install -r requirements.txt

Start:
- Double-click run.bat, or
- Run: python countdown_timer.py


3) Use it in Discord (voice channel)
------------------------------------
To send timer audio into Discord, use VB-Audio Virtual Cable:

1. Download and install VB-Cable:
   https://vb-audio.com/Cable/

2. In Windows Sound settings:
   - Set default Playback device to:
     CABLE Input (VB-Audio Virtual Cable)

3. In Discord:
   Settings > Voice & Video
   - Input Device: CABLE Output (VB-Audio Virtual Cable)

4. Start the timer and join a voice channel.
   People in channel should hear the spoken countdown.


4) Troubleshooting
------------------
No sound in browser:
- Click TEST VOICE first.
- Make sure page volume slider is above 0.
- Check Windows volume mixer for the browser.
- Allow autoplay/audio for the site/tab if blocked.

Cloud voice not speaking:
- Confirm internet is available.
- Switch to Local Microsoft/System Voice mode.

Discord cannot hear timer:
- Recheck VB-Cable routing (Windows Playback + Discord Input).
- Confirm Discord Input sensitivity is not cutting off audio.

