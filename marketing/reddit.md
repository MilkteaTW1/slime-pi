# Reddit drafts

Status: drafts, nothing posted. Read each subreddit's current rules before posting; both have rules about self-promotion and flair. Post from an account with some normal comment history, reply to comments for the first few hours, and don't cross-post the same day.

---

## r/raspberry_pi

**Flair:** Show-and-Tell (check the current flair list)

**Title:**
I gave my idle Pi 3 a pet slime whose mood follows CPU temp, load and network

**Body:**

My Pi 3 runs a couple of small things and I only ever looked at it when something broke. So I wrote a small creature that lives on it.

What it reads, every 30 seconds:
- `/sys/class/thermal/thermal_zone0/temp`
- load average and `/proc/meminfo`
- a TCP connect to 1.1.1.1:53 to check the internet (every 5 min, or every tick while offline)
- `who`, to notice SSH logins

What it does with that:
- 65 °C+: red and sweating. Load 1.5+ or low memory: panting. Offline: dazed. 23:00 to 07:00 and idle: asleep. No login for 3 days: sulking.
- Greets you when you SSH in. The first login of the day it pings your own /24 (nice 19, 8 at a time), checks ports 22/80/443/445/8080 on whatever answers, and writes a short "expedition report": what's on the network, what's new, what disappeared.
- You can drag files onto its web page to feed it. It reads and discards the bytes and keeps only name/size/extension. The file type it eats most sets its personality.

Resource side, since that's the first question I'd ask:
- user systemd service, `CPUQuota=10%`, `MemoryMax=64M`, `Nice=19`
- Python standard library only, nothing to pip install
- if the Pi stays critically short (<5% memory, load > 2x cores, or 80 °C) for about 90 s, it announces it on the page and via `wall`, waits 30 s and exits. It doesn't restart itself.

Tested on a Pi 3 Model B with Bookworm 64-bit. I'd really like to know how it behaves on a Zero 2 W, Pi 4 and Pi 5.

Code (MIT): https://github.com/MilkteaTW1/slime-pi

[GIF]

---

## r/tamagotchi

**Flair:** whatever fits "fan project" / "other" (check)

**Title:**
I made a tamagotchi-style pet that lives on a Raspberry Pi and reacts to the computer's real "health"

**Body:**

Not a real Tamagotchi and not trying to be one, but I think people here will get it.

It's a slime that lives on a Raspberry Pi (a tiny always-on computer). Instead of a hunger meter, its mood comes from the computer itself:

- the Pi gets hot → it turns red and sweats
- the Pi is busy → it pants
- the internet drops → it gets dizzy
- late at night → it sleeps
- you don't visit for 3 days → it sulks

You "feed" it by dragging files onto its page. Feed it mostly photos and it becomes dreamy and pink; mostly code and it becomes snakey and green. It grows from baby to kid to adult to elder (it gets a crown at the end), based on how long it has lived and how much you feed and poke it.

It also goes on a little walk around your home network once a day and comes back with a report of who it met.

There's no app or account. You need a Raspberry Pi and it shows up in a browser on your phone. Free and open source: https://github.com/MilkteaTW1/slime-pi

Happy to hear ideas for new moods or growth stages.

[GIF]
