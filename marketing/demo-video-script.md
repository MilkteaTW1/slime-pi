# Demo video script (about 50 seconds)

Status: draft. Vertical 9:16 for Shorts/Reels/Threads; the same shots work in 16:9 for YouTube and Hackaday. No voice-over needed: on-screen captions carry it, with quiet room sound or soft music. Captions in English; swap for the zh-TW lines in brackets for the Chinese cut.

Before filming:
- Install on the Pi, let it run a day so it is past "newborn" and has a diary.
- Have a phone and a laptop on the same Wi-Fi.
- For the hot shot: run a CPU load (`stress -c 4` or `yes > /dev/null` x4) on a Pi without a fan until it passes 65 °C. Takes a few minutes on a Pi 3.
- For the goodbye shot: `SLIME_FORCE_PRESSURE=memory python3 slime.py run` on a test copy.
- Blur MAC addresses and hostnames in the expedition report.

| Time | Picture | Caption |
|---|---|---|
| 0:00–0:04 | Close-up of a Pi 3 on a shelf, LEDs blinking. Hard cut to phone showing the slime, idle and bobbing. | This Raspberry Pi has a pet. [這台樹莓派有養寵物。] |
| 0:04–0:10 | Laptop terminal: `ssh pi@raspberrypi.local`. Cut to phone: slime greets, speech bubble visible. | It notices when I log in. [我一登入牠就知道。] |
| 0:10–0:18 | Split or quick cuts: terminal running a load, temp number rising on the page, slime turns red and sweats. | Over 65 °C, it sweats. [超過 65 °C 牠會流汗。] |
| 0:18–0:22 | Unplug Ethernet / turn off router Wi-Fi. Eyes spin. | No internet: dizzy. [斷網：頭暈。] |
| 0:22–0:32 | Drag three `.py` files from the laptop onto the page. Each one: nom bubble. After the third, colour shifts and trait label changes to "snakey". | Feed it files. It keeps only the name. Three .py files later: snakey. [餵牠檔案，只記檔名。吃了三個 .py：變蛇味。] |
| 0:32–0:40 | Scroll to the expedition report: devices list with one marked new. | Once a day it walks the home network and reports back. [每天在家裡網路走一圈，回來寫報告。] |
| 0:40–0:46 | Goodbye bubble on the page, then terminal showing the `wall` message. | If the Pi runs short, it says bye and gets out of the way. [Pi 不夠用時，牠會道別然後讓路。] |
| 0:46–0:52 | Back to the shelf shot, then end card: name, "one Python file, no dependencies", GitHub URL. | slime-pi · github.com/MilkteaTW1/slime-pi |

Notes:
- Keep each caption on screen at least 2 seconds; under 8 words where possible.
- Do not speed up the temperature shot so much that the number becomes unreadable; a visible "12 min later" card is fine.
- First 2 seconds decide whether people keep watching, so the slime should be on screen by 0:02.
