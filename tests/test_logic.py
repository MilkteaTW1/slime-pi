"""Pet logic tests. The Pi is mocked (files under /proc and /sys, `who`, `ip`, ping, sockets),
so these run on any computer, including Windows and macOS."""
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import slime  # noqa: E402


def fake_files(files):
    """Patch slime.rd so it returns canned contents for given paths."""
    return mock.patch.object(slime, "rd", side_effect=lambda path, default="": files.get(path, default))


MEMINFO = "MemTotal:        1000000 kB\nMemFree:          100000 kB\nMemAvailable:     250000 kB\n"


class ReadingThePi(unittest.TestCase):
    def test_cpu_temp(self):
        with fake_files({"/sys/class/thermal/thermal_zone0/temp": "48312\n"}):
            self.assertAlmostEqual(slime.cpu_temp(), 48.312)

    def test_cpu_temp_missing_sensor(self):
        with fake_files({}):
            self.assertEqual(slime.cpu_temp(), 0.0)

    def test_mem_free(self):
        with fake_files({"/proc/meminfo": MEMINFO}):
            self.assertAlmostEqual(slime.mem_free(), 0.25)

    def test_mem_free_unreadable_is_treated_as_plenty(self):
        for text in ("", "garbage", "MemTotal: 0 kB\nMemAvailable: 0 kB\n"):
            with fake_files({"/proc/meminfo": text}):
                self.assertEqual(slime.mem_free(), 1.0, text)

    def test_online(self):
        with mock.patch.object(socket, "create_connection") as cc:
            self.assertTrue(slime.online())
            cc.side_effect = OSError("no route")
            self.assertFalse(slime.online())

    def test_sessions(self):
        out = subprocess.CompletedProcess([], 0, stdout="pi pts/0 ...\npi pts/1 ...\n")
        with mock.patch.object(subprocess, "run", return_value=out):
            self.assertEqual(slime.sessions(), 2)
        with mock.patch.object(subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(slime.sessions(), 0)

    def test_system_locale_env_wins(self):
        with mock.patch.dict(os.environ, {"SLIME_LANG": "ja_JP.UTF-8"}):
            self.assertEqual(slime.system_locale(), "ja_JP.UTF-8")

    def test_system_locale_from_etc_default(self):
        env = {k: v for k, v in os.environ.items() if k not in ("SLIME_LANG", "LC_ALL", "LANGUAGE", "LANG")}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("builtins.open", mock.mock_open(read_data='# hi\nLANG="zh_TW.UTF-8"\n')):
            self.assertEqual(slime.system_locale(), "zh_TW.UTF-8")


class MoodEdges(unittest.TestCase):
    d = staticmethod(slime.decide)

    def test_thresholds_are_inclusive(self):
        self.assertEqual(self.d(65, 0, 12, True, .5, 0), "hot")
        self.assertEqual(self.d(64.9, 0, 12, True, .5, 0), "chill")
        self.assertEqual(self.d(50, 1.5, 12, True, .5, 0), "panting")
        self.assertEqual(self.d(50, 0, 12, True, .09, 0), "panting")   # memory almost full

    def test_night_window(self):
        for hour, mood in ((22, "happy"), (23, "sleeping"), (0, "sleeping"), (6, "sleeping"), (7, "happy")):
            self.assertEqual(self.d(45, .1, hour, True, .5, 0), mood, hour)

    def test_busy_night_does_not_sleep(self):
        self.assertEqual(self.d(55, .6, 2, True, .5, 0), "chill")

    def test_sulking_needs_three_days(self):
        self.assertEqual(self.d(45, .1, 12, True, .5, 2.9), "happy")
        self.assertEqual(self.d(45, .1, 12, True, .5, 3), "sulking")

    def test_every_mood_has_face_trait_and_words(self):
        w = slime.Words()
        for mood, trait in slime.TRAIT_BY_MOOD.items():
            self.assertIn(mood, slime.FACES)
            self.assertIn(trait, slime.TRAIT_HUE)
            for tag in w.all:
                w.set(tag)
                self.assertNotEqual(w.tr("say." + mood), "say." + mood, (tag, mood))
                self.assertNotEqual(w.tr("mood." + mood), "mood." + mood, (tag, mood))


class PressureEdges(unittest.TestCase):
    def test_critical_beats_tight(self):
        self.assertEqual(slime.pressure(90, 9, .03, 4), (2, "memory"))   # memory checked first
        self.assertEqual(slime.pressure(90, 9, .5, 4), (2, "cpu"))

    def test_scales_with_cores(self):
        self.assertEqual(slime.pressure(50, 3, .5, 1), (2, "cpu"))
        self.assertEqual(slime.pressure(50, 3, .5, 4), (0, ""))
        self.assertEqual(slime.pressure(76, 0, .5, 4), (1, "heat"))


class GrowthAndTraits(unittest.TestCase):
    def state(self, **kw):
        st = {"secs": 0, "food": {"n": 0, "ext": {}, "bytes": 0}, "pokes": 0, "moods": {}}
        st.update(kw)
        return st

    def test_xp(self):
        st = self.state(secs=7200, food={"n": 2, "ext": {}, "bytes": 0}, pokes=10)
        self.assertAlmostEqual(slime.xp(st), 2 + 10 + 2)

    def test_stage_boundaries(self):
        for hours, stage in ((19.9, "baby"), (20, "kid"), (100, "adult"), (399, "adult"), (400, "elder")):
            self.assertEqual(slime.stage_of(self.state(secs=hours * 3600)), stage, hours)

    def test_newborn(self):
        self.assertEqual(slime.trait_of(self.state()), "newborn")
        self.assertEqual(slime.trait_of(self.state(secs=899, moods={"hot": 899})), "newborn")

    def test_needs_three_meals_for_food_trait(self):
        st = self.state(secs=99999, food={"n": 2, "ext": {".py": 2}, "bytes": 0}, moods={"happy": 1})
        self.assertEqual(slime.trait_of(st), "sunny")

    def test_unknown_food_falls_back_to_mood(self):
        st = self.state(secs=99999, food={"n": 9, "ext": {".txt": 9}, "bytes": 0}, moods={"chill": 1})
        self.assertEqual(slime.trait_of(st), "easygoing")

    def test_old_mood_name_does_not_crash(self):
        # bug: a saved state with a mood this version does not know raised KeyError in /state
        st = self.state(secs=99999, moods={"grumpy": 500, "happy": 1})
        self.assertIn(slime.trait_of(st), slime.TRAIT_HUE)


class Diary(unittest.TestCase):
    def test_note_keeps_last_40(self):
        st = {"diary": []}
        for i in range(55):
            slime.note(st, "ev.woke", i)
        self.assertEqual(len(st["diary"]), 40)
        self.assertEqual(st["diary"][0]["a"], [15])

    def test_every_entry_kind_renders_in_every_language(self):
        entries = [
            {"t": 0, "k": "ev.ate", "a": ["cat.jpg", ".jpg"]},
            {"t": 0, "k": "ev.stopping", "a": ["heat"]},
            {"t": 0, "k": "ev.mood", "a": ["happy", "hot", 66, 0.4]},
            {"t": 0, "k": "ev.login", "a": ["ev.greet_back"]},
            {"t": 0, "k": "ev.login", "a": ["ev.greet_long", 5]},
            {"t": 0, "k": "ev.woke", "a": []},
            {"t": 0, "k": "report.diary", "a": [6, 1]},
            {"t": 0, "k": "idle", "a": [0]},
            {"t": 0, "text": "prototype entry"},
        ]
        w = slime.Words()
        for tag in w.all:
            w.set(tag)
            for e in entries:
                text = slime.render_entry(w, e)
                self.assertIsInstance(text, str, (tag, e))
                self.assertNotIn("{0}", text, (tag, e))

    def test_idle_index_survives_language_with_fewer_lines(self):
        # bug: diary keeps the idle index; a language with fewer idle lines raised IndexError
        w = slime.Words()
        w.all = {"en": {"idle": ["a", "b", "c"]}, "xx": {"idle": ["only one"]}}
        w.tag = "xx"
        self.assertEqual(slime.render_entry(w, {"t": 0, "k": "idle", "a": [2]}), "only one")
        self.assertEqual(slime.idle_line(w, 2), "only one")


class Report(unittest.TestCase):
    def setUp(self):
        self.w = slime.Words()
        self.w.set("en")

    def dev(self, name, new=False, kind="ssh"):
        return {"mac": name, "ip": "192.168.0.9", "name": name, "kind": kind, "new": new}

    def test_none(self):
        self.assertIsNone(slime.render_report(self.w, {"report": None}))

    def test_empty_walk(self):
        r = slime.render_report(self.w, {"report": {"t": 1, "gate": "", "found": [], "gone": []}})
        self.assertEqual(r["lines"][0], self.w.tr("report.none"))

    def test_new_device_story(self):
        st = {"report": {"t": 1, "gate": "192.168.0.1", "gone": ["old"],
                         "found": [self.dev("router", kind="gate"), self.dev("laptop", new=True)]}}
        lines = slime.render_report(self.w, st)["lines"]
        self.assertEqual(lines[-1], self.w.tr("report.story_new", "laptop"))   # new beats gone
        self.assertTrue(any(self.w.tr("report.new_tag") in ln for ln in lines))

    def test_gone_and_quiet_stories(self):
        st = {"report": {"t": 1, "gate": "", "gone": ["tv"], "found": [self.dev("nas", kind="share")]}}
        self.assertEqual(slime.render_report(self.w, st)["lines"][-1], self.w.tr("report.story_gone", "tv"))
        st["report"]["gone"] = []
        self.assertEqual(slime.render_report(self.w, st)["lines"][-1], self.w.tr("report.story_quiet"))

    def test_lists_at_most_eight(self):
        st = {"report": {"t": 1, "gate": "", "gone": [], "found": [self.dev(f"d{i}") for i in range(20)]}}
        lines = slime.render_report(self.w, st)["lines"]
        self.assertEqual(len(lines), 1 + 8 + 1)


class LanWalk(unittest.TestCase):
    IP_ADDR = "2: wlan0    inet 192.168.0.42/24 brd 192.168.0.255 scope global dynamic wlan0\n"
    ROUTE = "default via 192.168.0.1 dev wlan0\n"
    NEIGH = ("192.168.0.1 dev wlan0 lladdr aa:aa:aa:aa:aa:01 REACHABLE\n"
             "192.168.0.7 dev wlan0 lladdr aa:aa:aa:aa:aa:07 STALE\n"
             "192.168.0.8 dev wlan0 lladdr aa:aa:aa:aa:aa:08 STALE\n"
             "192.168.0.99 dev wlan0  FAILED\n")

    def run_walk(self, ip_addr=IP_ADDR, open_ports=None):
        open_ports = open_ports or {}

        def out(cmd, timeout=5):
            if cmd[:3] == ["ip", "-4", "-o"]:
                return ip_addr
            if cmd[:3] == ["ip", "-4", "route"]:
                return self.ROUTE
            if cmd[:3] == ["ip", "-4", "neigh"]:
                return self.NEIGH
            if cmd[:2] == ["getent", "hosts"]:
                return "192.168.0.7  nas.lan\n" if cmd[2] == "192.168.0.7" else ""
            return ""

        pings = []
        with mock.patch.object(slime, "_out", side_effect=out), \
                mock.patch.object(slime, "_open", side_effect=lambda ip, pt: pt in open_ports.get(ip, ())), \
                mock.patch.object(subprocess, "run", side_effect=lambda cmd, **kw: pings.append(cmd[-1])):
            return slime.lan_walk(), pings

    def test_walk(self):
        res, pings = self.run_walk(open_ports={"192.168.0.7": {445}, "192.168.0.8": {22, 80}})
        self.assertEqual(len(pings), 253)                       # whole /24 except itself
        self.assertNotIn("192.168.0.42", pings)
        self.assertEqual(res["gate"], "192.168.0.1")
        found = {d["ip"]: d for d in res["found"]}
        self.assertEqual(set(found), {"192.168.0.1", "192.168.0.7", "192.168.0.8"})  # FAILED skipped
        self.assertEqual(found["192.168.0.1"]["kind"], "gate")
        self.assertEqual(found["192.168.0.7"], {"mac": "aa:aa:aa:aa:aa:07", "ip": "192.168.0.7",
                                                "name": "nas", "kind": "share"})
        self.assertEqual(found["192.168.0.8"]["kind"], "ssh")   # ssh wins over web
        self.assertEqual(found["192.168.0.8"]["name"], "#8")    # no hostname: last octet

    def test_refuses_public_address(self):
        res, pings = self.run_walk(ip_addr="2: eth0    inet 8.8.4.4/24 scope global eth0\n")
        self.assertIsNone(res)
        self.assertEqual(pings, [])

    def test_no_network(self):
        self.assertEqual(self.run_walk(ip_addr="")[0], None)


class StateFile(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        p = mock.patch.object(slime, "STATE", os.path.join(self.dir.name, "state.json"))
        p.start()
        self.addCleanup(p.stop)

    def test_fresh(self):
        st = slime.load_state()
        self.assertEqual(st["food"]["n"], 0)
        self.assertEqual(st["diary"], [])

    def test_corrupt_file_gives_fresh_slime(self):
        with open(slime.STATE, "w") as f:
            f.write("{not json")
        self.assertEqual(slime.load_state()["secs"], 0)

    def test_prototype_ticks_are_migrated(self):
        with open(slime.STATE, "w") as f:
            json.dump({"ticks": 360, "pokes": 3}, f)
        st = slime.load_state()
        self.assertEqual(st["secs"], 3600)
        self.assertEqual(st["pokes"], 3)
        self.assertIn("devices", st)   # missing keys filled in


class Upload(unittest.TestCase):
    def test_read_length(self):
        for raw, n in ((None, 0), ("", 0), ("12", 12), ("-5", 0), ("abc", 0)):
            self.assertEqual(slime.read_length(raw), n, raw)

    def test_drain(self):
        self.assertEqual(slime.drain(io.BytesIO(b"x" * 200000), 200000), 200000)

    def test_drain_stops_when_client_hangs_up(self):
        # bug: the old loop did `left -= len(read())`; a short body made it spin forever at 100% CPU
        self.assertEqual(slime.drain(io.BytesIO(b"x" * 10), 1000), 10)

    def test_drain_stops_on_stalled_client(self):
        class Stalled:
            def read(self, n):
                raise TimeoutError("timed out")
        self.assertEqual(slime.drain(Stalled(), 1000), 0)


if __name__ == "__main__":
    unittest.main()
