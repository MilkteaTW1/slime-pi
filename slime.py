#!/usr/bin/env python3
"""A slime that lives in your Raspberry Pi. Standard library only.

  slime.py run     run the slime (service); also serves http://<pi>:8077
  slime.py look    print the slime in the terminal

Designed to cost almost nothing: it wakes every 30 seconds, reads a few files,
and only does real work (language check, LAN walk) when someone logs in.
Dropped files are never stored; only name, size and extension are remembered.
"""
import concurrent.futures
import ipaddress
import json
import os
import random
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~/.slime")
STATE = os.path.join(HOME, "state.json")
LOCALES = os.path.join(HERE, "locales")
PORT = int(os.environ.get("SLIME_PORT", "8077"))
TICK = 30                     # seconds between samples
SAVE_EVERY = 10               # ticks between disk writes (5 minutes)
MAX_FOOD = 5 * 1024 * 1024
EXPLORE_COOLDOWN = 600
STOPPED = os.path.join(HOME, "stopped.json")
STOP_AFTER = 3                # critical ticks in a row (about 90 s) before it leaves
GOODBYE_SECS = 30             # how long users get to read the goodbye
STAGES = [(0, "baby"), (20, "kid"), (100, "adult"), (400, "elder")]
TRAIT_BY_EXT = {".py": "snakey", ".js": "jittery", ".pdf": "scholarly", ".jpg": "dreamy",
                ".png": "dreamy", ".mp3": "musical", ".mp4": "dramatic", ".zip": "stocky",
                ".exe": "spicy", ".xlsx": "tidy", ".docx": "tidy"}
TRAIT_HUE = {"snakey": 120, "jittery": 55, "scholarly": 205, "dreamy": 310, "musical": 275,
             "dramatic": 345, "stocky": 25, "spicy": 8, "tidy": 180, "newborn": 140, "sleepy": 230,
             "hothead": 5, "hustler": 40, "lonely": 280, "sunny": 95, "easygoing": 160, "clingy": 330}
TRAIT_BY_MOOD = {"sleeping": "sleepy", "hot": "hothead", "panting": "hustler", "dazed": "lonely",
                 "happy": "sunny", "chill": "easygoing", "sulking": "clingy"}
FACES = {
    "sleeping": ("  ___  ", " ( -.- ) z", "(_______)"),
    "hot":      ("  ___  ", " ( >.< ) ;", "(~~~~~~~)"),
    "panting":  ("  ___  ", " ( O.O ) ", "(_______)"),
    "dazed":    ("  ___  ", " ( @.@ ) ?", "(_______)"),
    "happy":    ("  ___  ", " ( ^.^ ) *", "(_______)"),
    "chill":    ("  ___  ", " ( o.o ) ", "(_______)"),
    "sulking":  ("  ___  ", " ( -.- ) ", "(_______)"),
}


# ---------- languages ----------

def load_locales():
    out = {}
    for f in sorted(os.listdir(LOCALES)):
        if f.endswith(".json"):
            with open(os.path.join(LOCALES, f), encoding="utf-8") as fh:
                out[f[:-5]] = json.load(fh)
    return out


def pick_locale(tag, available):
    """'zh_TW.UTF-8' -> 'zh-TW'; falls back to same language, then English."""
    tag = re.split(r"[.@]", tag or "")[0].replace("_", "-")
    if tag in available:
        return tag
    base = tag.split("-")[0].lower()
    for name in available:
        if name.split("-")[0].lower() == base:
            return name
    return "en"


def system_locale():
    """Language of this Pi. Only called at start and when someone logs in."""
    for key in ("SLIME_LANG", "LC_ALL", "LANGUAGE"):
        if os.environ.get(key):
            return os.environ[key].split(":")[0]
    try:
        for line in open("/etc/default/locale"):
            m = re.match(r'\s*(?:LC_ALL|LANG)\s*=\s*"?([^"\s]+)', line)
            if m:
                return m.group(1)
    except OSError:
        pass
    return os.environ.get("LANG", "en")


class Words:
    def __init__(self):
        self.all = load_locales()
        self.tag = "en"

    def set(self, locale_tag):
        self.tag = pick_locale(locale_tag, self.all)

    def get(self, path, *args):
        for tag in (self.tag, "en"):
            node = self.all.get(tag, {})
            for part in path.split("."):
                node = node.get(part) if isinstance(node, dict) else None
            if node is not None:
                return node.format(*args) if isinstance(node, str) and args else node
        return path

    tr = get

    def taste(self, ext):
        for tag in (self.tag, "en"):
            t = self.all.get(tag, {}).get("taste", {})
            if ext in t:
                return t[ext]
        return self.get("taste.default")


# ---------- reading the Pi ----------

def rd(path, default=""):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return default


def cpu_temp():
    try:
        return int(rd("/sys/class/thermal/thermal_zone0/temp")) / 1000
    except ValueError:
        return 0.0


def mem_free():
    try:
        m = {k: int(v.split()[0]) for k, v in (l.split(":") for l in rd("/proc/meminfo").splitlines())}
        return m["MemAvailable"] / m["MemTotal"]
    except (KeyError, ValueError):
        return 1.0


def online():
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=1.5).close()
        return True
    except OSError:
        return False


def sessions():
    try:
        return len(subprocess.run(["who"], capture_output=True, text=True, timeout=3).stdout.splitlines())
    except (OSError, subprocess.SubprocessError):
        return 0


def decide(temp, load, hour, net, memfree, absent_days):
    if not net:
        return "dazed"
    if temp >= 65:
        return "hot"
    if load >= 1.5 or memfree < 0.1:
        return "panting"
    if (hour >= 23 or hour < 7) and load < 0.5:
        return "sleeping"
    if absent_days >= 3:
        return "sulking"
    if temp < 50 and load < 0.3:
        return "happy"
    return "chill"


def pressure(temp, load, memfree, cores, forced=None):
    """(level, reason). 0 fine, 1 getting tight (stop optional work), 2 critical (leave the Pi alone)."""
    if forced:
        return 2, forced
    if memfree < 0.05:
        return 2, "memory"
    if load > cores * 2:
        return 2, "cpu"
    if temp >= 80:
        return 2, "heat"
    if memfree < 0.10:
        return 1, "memory"
    if load > cores * 1.25:
        return 1, "cpu"
    if temp >= 75:
        return 1, "heat"
    return 0, ""


# ---------- exploring the home network ----------

def _out(cmd, timeout=5):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def lan_walk():
    """Gently look around the /24 this Pi is on. Low priority, small thread pool."""
    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/", _out(["ip", "-4", "-o", "addr", "show", "scope", "global"]))
    if not m:
        return None
    me = ipaddress.ip_address(m.group(1))
    if not me.is_private:
        return None
    net = ipaddress.ip_network(f"{me}/24", strict=False)
    gate = (re.search(r"default via (\S+)", _out(["ip", "-4", "route", "show", "default"])) or [None, ""])[1]

    def ping(ip):
        subprocess.run(["nice", "-n", "19", "ping", "-c1", "-W1", str(ip)],
                       capture_output=True, timeout=4)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(lambda ip: _safe(ping, ip), [h for h in net.hosts() if h != me]))
    seen = {}
    for line in _out(["ip", "-4", "neigh"]).splitlines():
        p = line.split()
        if len(p) >= 5 and "lladdr" in p and p[-1] not in ("FAILED", "INCOMPLETE"):
            seen[p[p.index("lladdr") + 1]] = p[0]

    def probe(item):
        mac, ip = item
        ports = {pt for pt in (22, 80, 443, 445, 8080) if _open(ip, pt)}
        name = _out(["getent", "hosts", ip], 2).split()
        name = name[1].split(".")[0] if len(name) > 1 else "#" + ip.rsplit(".", 1)[1]
        kind = ("gate" if ip == gate else "ssh" if 22 in ports else "web" if ports & {80, 443, 8080}
                else "share" if 445 in ports else "stranger")
        return {"mac": mac, "ip": ip, "name": name, "kind": kind}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        return {"gate": gate, "found": list(ex.map(probe, seen.items()))}


def _safe(fn, *a):
    try:
        fn(*a)
    except Exception:
        pass


def _open(ip, port):
    try:
        socket.create_connection((ip, port), timeout=0.3).close()
        return True
    except OSError:
        return False


# ---------- state ----------

def load_state():
    st = {"born": time.time(), "moods": {}, "secs": 0, "food": {"n": 0, "ext": {}, "bytes": 0},
          "diary": [], "last_login": time.time(), "logins": 0, "pokes": 0, "devices": {}, "report": None}
    try:
        with open(STATE) as f:
            saved = json.load(f)
        if "secs" not in saved:
            saved["secs"] = saved.get("ticks", 0) * 10  # states from the first prototype
        st.update(saved)
    except (OSError, ValueError):
        pass
    return st


def xp(st):
    return st["secs"] / 3600 + st["food"]["n"] * 5 + st["pokes"] * 0.2


def stage_of(st):
    x = xp(st)
    return [n for t, n in STAGES if x >= t][-1]


def trait_of(st):
    ext = st["food"]["ext"]
    if st["food"]["n"] >= 3 and ext:
        top = max(ext, key=ext.get)
        if top in TRAIT_BY_EXT:
            return TRAIT_BY_EXT[top]
    if st["secs"] < 900 or not st["moods"]:
        return "newborn"
    return TRAIT_BY_MOOD[max(st["moods"], key=st["moods"].get)]


def note(st, key, *args):
    st["diary"].append({"t": time.time(), "k": key, "a": list(args)})
    del st["diary"][:-40]


def render_entry(w, e):
    if "text" in e:  # prototype-era entry
        return e["text"]
    k, a = e["k"], e["a"]
    if k == "ev.ate":
        return w.tr(k, a[0], w.taste(a[1]))
    if k == "ev.stopping":
        return w.tr(k, w.tr("reason." + a[0]))
    if k == "ev.mood":
        return w.tr(k, w.tr("mood." + a[0]), w.tr("mood." + a[1]), a[2], a[3])
    if k == "ev.login":
        return w.tr(k, w.tr(a[0], *a[1:]))
    if k == "idle":
        return w.tr("idle")[a[0]]
    return w.tr(k, *a)


def render_report(w, st):
    r = st["report"]
    if not r:
        return None
    found = r["found"]
    lines = [w.tr("report.summary", len(found), sum(1 for d in found if d["new"]))] if found else [w.tr("report.none")]
    if r.get("gate"):
        lines.append(w.tr("report.gate", r["gate"]))
    for d in found[:8]:
        tag = f" [{w.tr('report.new_tag')}]" if d["new"] else ""
        lines.append(f"{w.tr('report.kind.' + d['kind'])}: {d['name']} ({d['ip']}){tag}")
    new = [d["name"] for d in found if d["new"]]
    if new:
        lines.append(w.tr("report.story_new", new[0]))
    elif r.get("gone"):
        lines.append(w.tr("report.story_gone", r["gone"][0]))
    else:
        lines.append(w.tr("report.story_quiet"))
    return {"t": r["t"], "title": w.tr("report.title"), "lines": lines}


# ---------- the service ----------

def run():
    os.makedirs(HOME, exist_ok=True)
    st = load_state()
    w = Words()
    w.set(system_locale())
    lock = threading.Lock()
    cur = {"bubble": None, "bubble_until": 0, "exploring": False, "last_explore": 0}

    def say(key, *args, secs=25):
        cur["bubble"], cur["bubble_until"] = (key, args), time.time() + secs

    def save():
        tmp = STATE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(st, f)
        os.replace(tmp, STATE)

    def explore():
        with lock:
            if cur["exploring"] or time.time() - cur["last_explore"] < EXPLORE_COOLDOWN or cur.get("pressure", 0):
                return  # busy, cooling down, or the Pi is short of resources
            cur["exploring"] = True
            cur["last_explore"] = time.time()
            say("ev.explore_go", secs=15)
        try:
            res = lan_walk()
        except Exception:
            res = None
        with lock:
            cur["exploring"] = False
            if not res:
                return
            before = {m: d for m, d in st["devices"].items()}
            prev_macs = set((st["report"] or {}).get("macs", []))
            now = time.time()
            for d in res["found"]:
                d["new"] = d["mac"] not in before
                st["devices"][d["mac"]] = {"first": before.get(d["mac"], {}).get("first", now), "last": now,
                                           "name": d["name"]}
            macs = [d["mac"] for d in res["found"]]
            gone = [before[m]["name"] for m in prev_macs if m not in macs and m in before]
            st["report"] = {"t": now, "gate": res["gate"], "found": res["found"], "gone": gone, "macs": macs}
            note(st, "report.diary", len(res["found"]), sum(1 for d in res["found"] if d["new"]))
            save()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def reply(self, body, ctype="application/json"):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/state":
                with lock:
                    self.reply(json.dumps(snapshot()).encode())
            else:
                with open(os.path.join(HERE, "web", "index.html"), "rb") as f:
                    self.reply(f.read(), "text/html; charset=utf-8")

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            if self.path == "/feed":
                if n > MAX_FOOD:
                    with lock:
                        say("ev.toobig", secs=10)
                    return self.reply(b'{"ok":false}')
                left = n  # read and drop the bytes: only name and size matter
                while left > 0:
                    left -= len(self.rfile.read(min(65536, left)))
                name = unquote(self.headers.get("X-Name", "mystery"))
                ext = os.path.splitext(name)[1].lower() or "(none)"
                with lock:
                    f = st["food"]
                    f["n"] += 1
                    f["bytes"] += n
                    f["ext"][ext] = f["ext"].get(ext, 0) + 1
                    say("ev.nom", w.taste(ext), secs=20)
                    note(st, "ev.ate", name[:40], ext)
                    cur["ate"] = time.time()
                    save()
            elif self.path == "/poke":
                with lock:
                    st["pokes"] += 1
                    if st["pokes"] % 7 == 0:
                        cur["bubble"], cur["bubble_until"] = ("poke", ()), time.time() + 6
            elif self.path == "/explore":
                threading.Thread(target=explore, daemon=True).start()
            self.reply(b'{"ok":true}')

    def bubble_text(mood):
        if cur["bubble"] and time.time() < cur["bubble_until"]:
            key, args = cur["bubble"]
            if key == "poke":
                return random.choice(w.tr("poke"))
            if key == "idle_i":
                return w.tr("idle")[args[0]]
            return w.tr(key, *args)
        return w.tr("say." + mood)

    def snapshot():
        t = time.time()
        trait, stage = trait_of(st), stage_of(st)
        return {"mood": cur.get("mood", "chill"), "bubble": bubble_text(cur.get("mood", "chill")),
                "temp": cur.get("temp", 0), "load": cur.get("load", 0), "age_days": round((t - st["born"]) / 86400, 2),
                "trait": trait, "trait_name": w.tr("trait." + trait), "hue": TRAIT_HUE[trait],
                "stage": stage, "stage_name": w.tr("stage." + stage), "food": st["food"],
                "diary": [{"t": e["t"], "text": render_entry(w, e)} for e in st["diary"][-8:][::-1]],
                "report": render_report(w, st), "exploring": cur["exploring"], "ate": cur.get("ate", 0),
                "lang": w.tag, "ui": w.tr("ui")}

    def bye(*_):
        with lock:
            save()
        os._exit(0)

    def goodbye(reason):
        """Tell the user, then leave so other programs get the room. systemd will not restart a clean exit."""
        with lock:
            say("ev.stopping", w.tr("reason." + reason), secs=GOODBYE_SECS + 60)
            note(st, "ev.stopping", reason)
            save()
            text = w.tr("ev.stopping", w.tr("reason." + reason))
        _safe(lambda: subprocess.run(["wall"], input=f"[slime] {text}", text=True, timeout=5))
        with open(STOPPED, "w") as f:
            json.dump({"t": time.time(), "reason": reason}, f)
        time.sleep(GOODBYE_SECS)  # the web page polls and shows the message meanwhile
        bye()

    signal.signal(signal.SIGTERM, bye)
    threading.Thread(target=ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever, daemon=True).start()

    if os.path.exists(STOPPED):
        os.remove(STOPPED)
        note(st, "ev.woke")
    cores, strained = os.cpu_count() or 1, 0
    net, last_net, prev_mood, prev_sess, tick = True, 0, None, sessions(), 0
    while True:
        t = time.time()
        if t - last_net > 300 or not net:
            net, last_net = online(), t
        temp, load = cpu_temp(), os.getloadavg()[0]
        sess = sessions()
        today = time.strftime("%Y-%m-%d")
        went_in = sess > prev_sess
        with lock:
            absent = (t - st["last_login"]) / 86400
            if went_in:
                w.set(system_locale())  # language is checked on login only
                st["logins"] += 1
                greet = ("ev.greet_back", ) if absent < 3 else ("ev.greet_long", int(absent))
                say(*greet, secs=30)
                note(st, "ev.login", *greet)
            if sess > 0:
                st["last_login"] = t
            prev_sess = sess
            mood = decide(temp, load, time.localtime().tm_hour, net, mem_free(), absent)
            if prev_mood and mood != prev_mood:
                note(st, "ev.mood", prev_mood, mood, round(temp), round(load, 1))
            prev_mood = mood
            st["moods"][mood] = st["moods"].get(mood, 0) + TICK
            st["secs"] += TICK
            if mood in ("chill", "happy") and random.random() < 0.015:
                i = random.randrange(len(w.tr("idle")))
                cur["bubble"], cur["bubble_until"] = ("idle_i", (i,)), t + 20
                note(st, "idle", i)
            level, why = pressure(temp, load, mem_free(), cores, os.environ.get("SLIME_FORCE_PRESSURE"))
            strained = strained + 1 if level == 2 else 0
            cur.update(mood=mood, temp=round(temp, 1), load=round(load, 2), pressure=level)
            tick += 1
            if tick % SAVE_EVERY == 0 or went_in:
                save()
            last_report = time.strftime("%Y-%m-%d", time.localtime(st["report"]["t"])) if st["report"] else ""
        if strained >= STOP_AFTER:
            goodbye(why)
        if went_in and last_report != today:  # first login of the day: go exploring
            threading.Thread(target=explore, daemon=True).start()
        time.sleep(TICK)


def look():
    import urllib.request
    w = Words()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/state", timeout=2) as r:
            s = json.load(r)
    except OSError:
        w.set(system_locale())
        try:
            with open(STOPPED) as f:
                info = json.load(f)
            sys.exit(w.tr("cli.stopped", time.strftime("%m/%d %H:%M", time.localtime(info["t"])),
                          w.tr("reason." + info["reason"])))
        except (OSError, ValueError, KeyError):
            sys.exit(w.tr("cli.not_running"))
    w.set(s["lang"])
    print("\n".join(FACES[s["mood"]]))
    print(f"\n\"{s['bubble']}\"")
    print(w.tr("cli.line", s["trait_name"], s["stage_name"], s["age_days"], s["food"]["n"], s["temp"], s["load"]))
    for d in s["diary"][:3]:
        print(" -", time.strftime("%m/%d %H:%M", time.localtime(d["t"])), d["text"])
    if s["report"]:
        print("\n" + s["report"]["title"])
        for line in s["report"]["lines"]:
            print(" *", line)


if __name__ == "__main__":
    {"run": run, "look": look}.get(sys.argv[1] if len(sys.argv) > 1 else "look", look)()
