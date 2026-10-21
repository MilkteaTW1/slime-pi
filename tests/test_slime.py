import os
import subprocess
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import slime  # noqa: E402


class Language(unittest.TestCase):
    def setUp(self):
        self.w = slime.Words()

    def test_pick_locale(self):
        av = {"en": 1, "zh-TW": 1}
        self.assertEqual(slime.pick_locale("zh_TW.UTF-8", av), "zh-TW")
        self.assertEqual(slime.pick_locale("zh_HK.UTF-8", av), "zh-TW")   # same language
        self.assertEqual(slime.pick_locale("en_GB.UTF-8", av), "en")
        self.assertEqual(slime.pick_locale("fr_FR.UTF-8", av), "en")      # fallback
        self.assertEqual(slime.pick_locale("C", av), "en")
        self.assertEqual(slime.pick_locale("", av), "en")

    def test_switch(self):
        self.w.set("zh_TW.UTF-8")
        self.assertIn("探險", self.w.tr("report.title"))
        self.w.set("en_GB.UTF-8")
        self.assertEqual(self.w.tr("report.title"), "Expedition report")

    def test_taste_fallback(self):
        self.assertEqual(self.w.taste(".nope"), self.w.tr("taste.default"))
        self.assertIn("snaky", self.w.taste(".py"))


class Mood(unittest.TestCase):
    def test_priorities(self):
        d = slime.decide
        self.assertEqual(d(70, 3, 12, False, .5, 0), "dazed")      # no network beats everything
        self.assertEqual(d(70, 3, 12, True, .5, 0), "hot")
        self.assertEqual(d(50, 2, 12, True, .5, 0), "panting")
        self.assertEqual(d(45, .1, 2, True, .5, 0), "sleeping")
        self.assertEqual(d(45, .1, 12, True, .5, 5), "sulking")
        self.assertEqual(d(45, .1, 12, True, .5, 0), "happy")
        self.assertEqual(d(55, .4, 12, True, .5, 0), "chill")


class Growth(unittest.TestCase):
    def state(self, **kw):
        st = {"secs": 0, "food": {"n": 0, "ext": {}, "bytes": 0}, "pokes": 0, "moods": {}}
        st.update(kw)
        return st

    def test_stage(self):
        self.assertEqual(slime.stage_of(self.state()), "baby")
        self.assertEqual(slime.stage_of(self.state(food={"n": 4, "ext": {}, "bytes": 0})), "kid")
        self.assertEqual(slime.stage_of(self.state(secs=500 * 3600)), "elder")

    def test_trait_from_food(self):
        st = self.state(secs=99999, food={"n": 5, "ext": {".py": 4, ".txt": 1}, "bytes": 0})
        self.assertEqual(slime.trait_of(st), "snakey")

    def test_trait_from_mood(self):
        st = self.state(secs=99999, moods={"sleeping": 900, "happy": 10})
        self.assertEqual(slime.trait_of(st), "sleepy")


class Entries(unittest.TestCase):
    def test_diary_follows_language(self):
        w = slime.Words()
        e = {"t": 0, "k": "ev.ate", "a": ["a.py", ".py"]}
        w.set("en")
        en = slime.render_entry(w, e)
        w.set("zh-TW")
        zh = slime.render_entry(w, e)
        self.assertNotEqual(en, zh)
        self.assertIn("a.py", zh)


class Locales(unittest.TestCase):
    def test_check_lang_passes(self):
        r = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "check-lang.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
