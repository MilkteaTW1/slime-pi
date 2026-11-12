# Hackaday.io project page (draft)

Status: draft, not posted. Hackaday.io fits this project better than Product Hunt (hardware-adjacent, no signup funnel, no product to sell). A shorter Product Hunt version is at the bottom in case you want it later.

---

## Project name

slime-pi

## Summary (max ~140 characters)

A virtual pet that lives on a Raspberry Pi. Its mood is the Pi's real CPU temperature, load and network. One Python file, no dependencies.

## Description

I had a Raspberry Pi 3 on a shelf running a couple of small services, and the only time I looked at it was when something broke. So I gave it a resident.

slime-pi is a small slime that lives on the Pi as a user systemd service. Every 30 seconds it reads `/sys/class/thermal`, `/proc/meminfo`, the load average and `who`, and decides how it feels:

- 65 °C or hotter: it goes red and sweats
- load 1.5+ or memory almost full: it pants
- no internet: its eyes spin
- 23:00 to 07:00 and idle: it sleeps
- nobody logged in for 3 days: it sulks

You see it on a web page served by the Pi itself (port 8077), or with `slime` in a terminal.

Things you can do with it:

- **Feed it files.** Drag a file onto the page. The bytes are read and dropped; only the name, size and extension are kept. After three meals, the file type it ate most sets its personality and colour: `.py` makes it snakey, images make it dreamy, `.exe` makes it spicy.
- **Log in over SSH.** It greets you. The first login of the day also sends it on an "expedition": it pings your own /24 at nice 19, eight at a time, checks five common ports on whatever answers, and writes a short report of who is on the network, who is new, and who disappeared.
- **Let it grow.** Hours alive, meals and pokes add up. It goes baby, kid, adult, elder, and grows a sprout, an antenna and a crown on the way.

The part I spent the most time on is making sure it never becomes the problem. systemd caps it at 10% of one core and 64 MB. Each tick it checks memory, load and temperature. When the Pi gets tight it skips optional work. If the Pi stays critical for about 90 seconds (under 5% memory, load over twice the core count, or 80 °C), it posts a goodbye in the page, sends a `wall` message to open terminals, writes it in its diary, waits 30 seconds and exits. It does not restart itself.

No pip installs, no GPIO, no wiring. English and Traditional Chinese are built in, and adding a language is one JSON file.

## Components

- Raspberry Pi (tested on Pi 3 Model B, Raspberry Pi OS Bookworm 64-bit)
- microSD card, 8 GB+
- Official power supply
- Any device with a browser on the same network

## Build log ideas (one per post)

1. Why a pet and not a dashboard: the mood table and how the priorities were picked.
2. The "step aside" logic: measuring pressure, the 90-second grace period, and why it never restarts itself.
3. The LAN expedition: keeping a /24 ping walk polite on a Pi 3 (nice 19, 8 workers, once a day).
4. Feeding files without storing them: reading and dropping the upload, and the bug where a client that hung up mid-upload made the server spin forever.
5. Request: photos and test reports from Pi Zero 2 W, Pi 4 and Pi 5.

## Links

- Code: https://github.com/MilkteaTW1/slime-pi
- Project page: https://inkacuity.com/projects/slime-pi

## Images to upload

- `docs/demo.en.gif` as the cover
- A real photo of the Pi with a phone showing the page (not taken yet)
- A screenshot of an expedition report (blur MAC addresses and hostnames)

---

## Product Hunt version (if you ever want it)

**Name:** slime-pi
**Tagline (60 chars max):** A pet whose mood is your Raspberry Pi's real health
**Topics:** Open Source, Raspberry Pi, Developer Tools, Games

**Description (260 chars max):**
A slime that lives on your Raspberry Pi. It sweats when the CPU is hot, pants under load, sleeps at night, and sulks if you don't SSH in for 3 days. Feed it files to shape its personality. One Python file, no dependencies, MIT.

**First comment (maker):**
I built this for a Pi 3 that sat on my shelf doing nothing interesting. It is free and open source, no account, nothing leaves your network. It caps itself at 10% CPU and 64 MB, and shuts itself down if the Pi runs short. Test reports from other Pi models are very welcome.
