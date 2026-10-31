import datetime
import os
import random
import shutil
import tempfile
import tkinter as tk
import unittest
from unittest import mock

from problem_trainer import app as A
from problem_trainer import appkit as ak
from problem_trainer import training as tr


class TestSyllabus(unittest.TestCase):
    def test_graph_is_acyclic_and_ordered(self):
        for t, (level, prereq, text) in tr.SYLLABUS.items():
            self.assertTrue(text)
            for p in prereq:
                self.assertIn(p, tr.SYLLABUS)
                self.assertLess(tr.SYLLABUS[p][0], level + 1, (t, p))

    def test_unlocking(self):
        self.assertTrue(tr.unlocked("Implementation", {}))
        self.assertFalse(tr.unlocked("Greedy", {}))
        self.assertEqual(tr.blocked_by("Greedy", {}), ["Sorting"])
        self.assertEqual(tr.next_topics({})[:1], ["Implementation"])
        strong = {"Implementation": 1200.0}
        self.assertIn("Sorting", tr.next_topics(strong))
        self.assertNotIn("Implementation", tr.next_topics(strong))


class TestSkill(unittest.TestCase):
    def test_update_directions(self):
        self.assertGreater(tr.update_skill(1000, 1000, True), 1000)
        self.assertLess(tr.update_skill(1000, 1000, False), 1000)
        easy = tr.update_skill(1000, 500, True) - 1000
        hard = tr.update_skill(1000, 1500, True) - 1000
        self.assertGreater(hard, easy)
        self.assertLess(tr.update_skill(1000, 1000, True, hints=1), tr.update_skill(1000, 1000, True))

    def test_converges_towards_true_level(self):
        rng = random.Random(1)
        true = 1600
        attempts = []
        for i in range(600):
            d = rng.randint(1000, 2200)
            attempts.append({"topic": "Greedy", "difficulty": d, "solved": rng.random() < tr.win_probability(true, d), "day": "2026-01-01", "id": i})
        self.assertAlmostEqual(tr.topic_skills(attempts)["Greedy"], true, delta=170)

    def test_replay_order_and_gaps(self):
        attempts = [{"topic": "Greedy", "difficulty": 1200, "solved": True, "day": "2026-01-02"},
                    {"topic": None, "difficulty": 1200, "solved": True, "day": "2026-01-01"},
                    {"topic": "Sorting", "difficulty": None, "solved": True, "day": "2026-01-01"}]
        self.assertEqual(list(tr.topic_skills(attempts)), ["Greedy"])
        self.assertEqual(tr.overall_skill({}), tr.START_SKILL)
        self.assertEqual(tr.overall_skill({"a": 1000.0, "b": 2000.0}), 1500)

    def test_mastery_bounds(self):
        self.assertEqual(tr.mastery("Implementation", {"Implementation": 5000}), 1)
        self.assertEqual(tr.mastery("Implementation", {"Implementation": 100}), 0)


class TestReviews(unittest.TestCase):
    def test_boxes(self):
        self.assertEqual(tr.schedule_after(0, True, False, "2026-01-01"), (1, "2026-01-04"))
        self.assertEqual(tr.schedule_after(3, False, False, "2026-01-01"), (0, "2026-01-02"))
        self.assertEqual(tr.schedule_after(2, True, True, "2026-01-01"), (2, "2026-01-08"))
        self.assertEqual(tr.schedule_after(len(tr.BOXES) - 1, True, False, "2026-01-01")[1], None)    # retired

    def test_due_order(self):
        ps = [{"review_on": "2026-01-03", "difficulty": 1}, {"review_on": "2026-01-01", "difficulty": 2}, {"review_on": None}, {"review_on": "2026-02-01"}]
        self.assertEqual([p["review_on"] for p in tr.due(ps, "2026-01-05")], ["2026-01-01", "2026-01-03"])


class TestLadder(unittest.TestCase):
    def bank(self):
        rng = random.Random(2)
        return [{"title": str(i), "topic": rng.choice(tr.TOPICS[:6]), "difficulty": rng.randint(800, 2400), "solved": i % 5 == 0} for i in range(200)]

    def test_constraints(self):
        rows = tr.build_ladder(self.bank(), 1400, 10, seed=1)
        self.assertEqual(len(rows), 10)
        self.assertTrue(all(not p["solved"] and 1300 <= p["difficulty"] <= 1700 for p in rows))
        same = sum(1 for a, b in zip(rows, rows[1:]) if a["topic"] == b["topic"])
        self.assertLessEqual(same, 2)

    def test_topic_filter_and_small_pool(self):
        rows = tr.build_ladder(self.bank(), 1400, 10, topics=["Greedy"], seed=1)
        self.assertTrue(all(p["topic"] == "Greedy" for p in rows))
        self.assertEqual(tr.build_ladder([], 1400), [])


class TestMisc(unittest.TestCase):
    def test_streaks(self):
        self.assertEqual(tr.streaks(["2026-03-01", "2026-03-02", "2026-03-03", "2026-03-05"], "2026-03-06"), (1, 3))
        self.assertEqual(tr.streaks([], "2026-03-06"), (0, 0))
        self.assertEqual(tr.streaks(["2026-03-01"], "2026-03-09"), (0, 1))

    def test_weekly(self):
        rows = [{"day": "2026-03-02", "solved": True}, {"day": "2026-03-03", "solved": False}, {"day": "2026-02-01", "solved": True}]
        v = tr.weekly_counts(rows, "2026-03-04", 4)
        self.assertEqual(v, [0, 0, 0, 1])

    def test_advice(self):
        day = "2026-03-10"
        self.assertIn("No attempts", tr.advice([], {}, day)[0])
        all_solved = [{"day": day, "solved": True, "topic": "Greedy", "hints": 0}] * 10
        self.assertTrue(any("harder" in x for x in tr.advice(all_solved, {}, day)))
        none = [{"day": day, "solved": False, "topic": "Greedy", "hints": 1}] * 10
        text = " ".join(tr.advice(none, {}, day))
        self.assertIn("step down", text)
        self.assertIn("hints", text)
        self.assertIn("one topic", text)

    def test_csv(self):
        rows = tr.parse_csv_rows("title,topic,difficulty,url\nAlpha,Greedy,1200,http://x\nBeta,Sorting,900\n")
        self.assertEqual([r["title"] for r in rows], ["Alpha", "Beta"])
        with self.assertRaises(ValueError):
            tr.parse_csv_rows("A,B,hard\n")


class TestGui(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = ak.Store(A.SCHEMA, os.path.join(self.dir, "t.sqlite3"), A.APP.APP_NAME)
        A.sample(self.store)
        try:
            self.app = A.APP(self.store)
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.errors = []
        self.app.report_callback_exception = lambda e, v, t: self.errors.append(repr(v))
        self.app.update()

    def tearDown(self):
        self.store.close()
        self.app.destroy()
        shutil.rmtree(self.dir, ignore_errors=True)
        self.assertEqual(self.errors, [])

    def test_every_screen_in_both_themes(self):
        for theme in ("Dark", "Light"):
            self.app.set_theme(theme)
            for t in self.app.titles():
                self.app.navigate(t)
                self.app.update()

    def test_logging_updates_everything(self):
        self.app.navigate("Problem bank")
        b = self.app.views["Problem bank"]
        pid = self.store.list("problem", "solved=0")[0]["id"]
        b.view.select(pid)
        n = self.store.count("attempt")
        b.log.minutes.set("25")
        b.log.go(True)
        self.assertEqual(self.store.count("attempt"), n + 1)
        p = self.store.get("problem", pid)
        self.assertEqual((p["solved"], p["box"]), (1, 1))
        self.assertIsNotNone(p["review_on"])
        b.log.go(False)
        self.assertEqual(self.store.get("problem", pid)["box"], 0)
        self.assertEqual(self.store.get("problem", pid)["solved"], 1)        # failing a review does not undo the solve
        b.log.minutes.set("x")
        with mock.patch("tkinter.messagebox.showerror") as err:
            b.log.go(True)
        self.assertTrue(err.called)

    def test_due_review_on_today(self):
        pid = self.store.list("problem")[0]["id"]
        self.store.update("problem", pid, review_on=ak.today())
        self.app.navigate("Today")
        v = self.app.views["Today"]
        self.assertTrue(v.due.tree.exists(str(pid)))
        v.due.tree.selection_set(str(pid))
        v.log.go(True)
        self.assertNotEqual(self.store.get("problem", pid)["review_on"], ak.today())

    def test_screens_with_data(self):
        self.app.navigate("Skills")
        s = self.app.views["Skills"]
        s.show("Greedy")
        self.assertIn("Exchange arguments", s.info.cget("text"))
        self.app.navigate("Ladder")
        self.assertTrue(self.app.views["Ladder"].table.tree.get_children())
        self.app.navigate("Problem bank")
        self.assertEqual(self.app.views["Problem bank"].load_csv("Gamma,Nonsense topic,1000\n"), 1)
        self.assertEqual(self.store.list("problem", "title='Gamma'")[0]["topic"], "Implementation")

    def test_empty_database(self):
        self.store.close()
        self.app.destroy()
        self.store = ak.Store(A.SCHEMA, os.path.join(self.dir, "e.sqlite3"), A.APP.APP_NAME)
        self.app = A.APP(self.store)
        for t in self.app.titles():
            self.app.navigate(t)
            self.app.update()


if __name__ == "__main__":
    unittest.main()
