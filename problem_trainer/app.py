"""Problem Trainer desktop program."""
import datetime
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from . import appkit as ak
from . import training as tr
from .appkit import Entity, Field, entities

SCHEMA = entities(
    Entity("problem", "Problem", "Problem bank", "title", [
        Field("title", "Title", required=True, list_col=True, width=30),
        Field("topic", "Topic", "choice", tr.TOPICS, default="Implementation", list_col=True, width=20),
        Field("difficulty", "Difficulty", "int", default=1200, list_col=True, width=9),
        Field("solved", "Solved", "bool", list_col=True, width=7),
        Field("review_on", "Next review", "date", list_col=True, width=11),
        Field("box", "Box", "int", default=0),
        Field("url", "Link"),
        Field("notes", "Key idea", "long"),
    ], "solved, difficulty, id"),
    Entity("attempt", "Attempt", "Attempts", "problem_id", [
        Field("problem_id", "Problem", "ref", ref="problem", required=True, list_col=True, width=30),
        Field("day", "Date", "date", required=True, list_col=True, width=11),
        Field("solved", "Solved", "bool", list_col=True, width=7),
        Field("hints", "Used hints", "bool", list_col=True, width=9),
        Field("minutes", "Minutes", "int", list_col=True, width=8),
        Field("notes", "Notes", "long"),
    ], "day DESC, id DESC"),
)
SAMPLE_BANK = [("Equal Pairs", "Hashing and maps", 1100), ("Fence Painting", "Greedy", 1200), ("Tallest Tower", "Sorting", 900),
               ("Budget Split", "Binary search", 1400), ("Longest Calm Stretch", "Two pointers", 1300), ("Treasure Grid", "Basic DP", 1500),
               ("Island Hopping", "Graph traversal", 1400), ("Cheapest Flight", "Shortest paths", 1700), ("Bit Toggle", "Bit manipulation", 1250),
               ("Range Totals", "Prefix sums", 1050), ("Subtree Sums", "Trees", 1750), ("Rolling Dice", "Basic DP", 1450),
               ("Coin Row", "Basic DP", 1300), ("Team Merge", "Disjoint sets", 1600), ("Prime Walk", "Number theory", 1550),
               ("Palindrome Checker", "Strings", 1850), ("Task Order", "Topological order and DAG DP", 1900)]


def sample(store):
    day = datetime.date.today()
    ids = [store.insert("problem", title=t + " (sample)", topic=a, difficulty=d) for t, a, d in SAMPLE_BANK]
    rows = [(0, True, False, 20, 12), (1, True, True, 45, 9), (2, True, False, 10, 8), (3, False, False, 60, 6), (3, True, True, 50, 4),
            (4, True, False, 25, 3), (5, False, False, 60, 2), (6, True, False, 35, 1), (9, True, False, 15, 1), (7, False, False, 40, 0)]
    for i, solved, hints, mins, ago in rows:
        record(store, ids[i], solved, hints, mins, (day - datetime.timedelta(days=ago)).isoformat())


def record(store, pid, solved, hints, minutes, day):
    """Log an attempt and move the problem between review boxes."""
    p = store.get("problem", pid)
    store.insert("attempt", problem_id=pid, day=day, solved=1 if solved else 0, hints=1 if hints else 0, minutes=minutes)
    box, review = tr.schedule_after(p["box"] or 0, solved, hints, day)
    store.update("problem", pid, box=box, review_on=review, solved=1 if (solved or p["solved"]) else 0)


def attempts_full(store):
    probs = {p["id"]: p for p in store.list("problem")}
    out = []
    for a in store.list("attempt"):
        p = probs.get(a["problem_id"])
        if p:
            out.append(dict(a, topic=p["topic"], difficulty=p["difficulty"], solved=bool(a["solved"]), hints=a["hints"]))
    return out


class LogPanel(ttk.Frame):
    """Record the result of working on a problem."""

    def __init__(self, parent, app, get_problem, on_done):
        super().__init__(parent, style="Panel.TFrame", padding=10)
        self.app, self.get_problem, self.on_done = app, get_problem, on_done
        self.minutes = tk.StringVar(value="30")
        self.hints = tk.IntVar()
        ttk.Label(self, text="Log your attempt", style="Head.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))
        ak.labeled_entry(self, "Minutes", self.minutes, 8, "PanelMuted.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(self, text="Used hints", variable=self.hints).grid(row=1, column=1, padx=8, sticky="s")
        ttk.Button(self, text="Solved", style="Accent.TButton", command=lambda: self.go(True)).grid(row=1, column=2, sticky="s")
        ttk.Button(self, text="Not solved", command=lambda: self.go(False)).grid(row=1, column=3, padx=6, sticky="s")

    def go(self, solved):
        pid = self.get_problem()
        if not pid:
            self.app.status("Select a problem first")
            return
        try:
            mins = int(self.minutes.get() or 0)
        except ValueError:
            messagebox.showerror("Attempt", "Minutes must be a whole number.", parent=self)
            return
        record(self.app.store, pid, solved, bool(self.hints.get()), mins, ak.today())
        self.hints.set(0)
        self.on_done()


class Today(ttk.Frame):
    title = "Today"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.top = ttk.Frame(self)
        self.top.pack(fill="x", pady=(0, 8))
        cols = ttk.Frame(self)
        cols.pack(fill="both", expand=True)
        cols.columnconfigure(0, weight=3, uniform="c")
        cols.columnconfigure(1, weight=2, uniform="c")
        cols.rowconfigure(0, weight=1)
        left, right = ttk.Frame(cols), ttk.Frame(cols)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(left, text="Reviews due today", style="Muted.TLabel").pack(anchor="w")
        self.due = ak.Table(left, app, [("title", "Problem", 30), ("topic", "Topic", 20), ("d", "Difficulty", 9), ("on", "Due", 11)], height=7)
        self.due.pack(fill="both", expand=True)
        self.log = LogPanel(left, app, self.selected, self.refresh)
        self.log.pack(fill="x", pady=6)
        p = ak.panel(right, "What to do next")
        p.pack(fill="both", expand=True)
        self.tips = ttk.Label(p, text="", style="Panel.TLabel", wraplength=int(380 * app.scale), justify="left")
        self.tips.pack(anchor="w")

    def selected(self):
        s = self.due.selected()
        return int(s) if s else None

    def refresh(self):
        store = self.app.store
        attempts = attempts_full(store)
        skills = tr.topic_skills(attempts)
        cur, longest = tr.streaks([a["day"] for a in attempts], ak.today())
        rows = tr.due(store.list("problem"), ak.today())
        for w in self.top.winfo_children():
            w.destroy()
        ak.tiles(self.top, [("Skill estimate", "%d" % tr.overall_skill(skills), "from your %d practised topics" % len(skills)),
                            ("Reviews due", str(len(rows)), "today"), ("Streak", "%d days" % cur, "longest %d" % longest),
                            ("Solved", str(store.count("problem", "solved=1")), "of %d in the bank" % store.count("problem"))]).pack(fill="x")
        self.due.fill([(r["id"], (r["title"], r["topic"], r["difficulty"] or "", r["review_on"])) for r in rows])
        nt = tr.next_topics(skills, 4)
        lines = ["Study next: %s" % ", ".join(nt) if nt else "Everything unlocked is mastered.", ""] + tr.advice(attempts, skills, ak.today())
        self.tips.configure(text="\n\n".join(lines))


class Bank(ttk.Frame):
    title = "Problem bank"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.view = ak.EntityView(self, app, "problem", skip=("box", "review_on"), buttons=[("Import CSV", self.import_csv), ("Open link", self.open_link)])
        self.view.pack(fill="both", expand=True)
        self.log = LogPanel(self, app, lambda: self.view.current, self.view.refresh)
        self.log.pack(fill="x", pady=(6, 0))
        self.refresh, self.commit = self.view.refresh, self.view.commit

    def open_link(self):
        p = self.app.store.get("problem", self.view.current) if self.view.current else None
        if p and p["url"]:
            webbrowser.open(p["url"])

    def import_csv(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("CSV", "*.csv"), ("All files", "*.*")])
        if path:
            with open(path, encoding="utf-8", errors="replace") as fh:
                self.load_csv(fh.read())

    def load_csv(self, text):
        try:
            rows = tr.parse_csv_rows(text)
        except ValueError as exc:
            messagebox.showerror("Import", str(exc), parent=self)
            return 0
        for r in rows:
            r["topic"] = r["topic"] if r["topic"] in tr.SYLLABUS else "Implementation"
            self.app.store.insert("problem", **r)
        self.view.refresh()
        self.app.status("Imported %d problems" % len(rows))
        return len(rows)


class Skills(ttk.Frame):
    title = "Skills"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True)
        left, right = ttk.Frame(pane), ak.panel(pane, "Topic")
        pane.add(left, weight=3)
        pane.add(right, weight=2)
        pane.bind("<Map>", lambda e: pane.after_idle(lambda: pane.sashpos(0, int(pane.winfo_width() * 0.6))))
        self.table = ak.Table(left, app, [("topic", "Topic", 28), ("level", "Level", 7), ("skill", "Skill", 7), ("mastery", "Mastery", 9), ("state", "State", 12)],
                              on_select=self.show)
        self.table.pack(fill="both", expand=True)
        self.info = ttk.Label(right, text="Select a topic.", style="Panel.TLabel", wraplength=int(340 * app.scale), justify="left")
        self.info.pack(anchor="w")
        self.skills = {}

    def refresh(self):
        self.skills = tr.topic_skills(attempts_full(self.app.store))
        rows = []
        for t in tr.TOPICS:
            m = tr.mastery(t, self.skills)
            state = "Mastered" if m >= 0.85 else "In progress" if tr.unlocked(t, self.skills) else "Locked"
            tag = "ok" if state == "Mastered" else "muted" if state == "Locked" else None
            rows.append((t, (t, tr.SYLLABUS[t][0], "%d" % self.skills.get(t, tr.START_SKILL), "%d%%" % (100 * m), state), tag))
        self.table.fill(rows)

    def show(self, t):
        if not t:
            return
        level, prereq, text = tr.SYLLABUS[t]
        block = tr.blocked_by(t, self.skills)
        self.info.configure(text="%s\n\nTypical level %d\n\n%s\n\nPrerequisites: %s%s" % (
            t, level, text, ", ".join(prereq) or "none", "\n\nStill needed: " + ", ".join(block) if block else ""))


class Ladder(ttk.Frame):
    title = "Ladder"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        top = ttk.Frame(self)
        top.pack(fill="x")
        self.count, self.low, self.high = tk.StringVar(value="8"), tk.StringVar(value="-200"), tk.StringVar(value="400")
        ak.labeled_entry(top, "Problems", self.count, 8).pack(side="left", padx=(0, 8))
        ak.labeled_entry(top, "From (relative to skill)", self.low, 10).pack(side="left", padx=(0, 8))
        ak.labeled_entry(top, "To (relative to skill)", self.high, 10).pack(side="left", padx=(0, 8))
        ttk.Button(top, text="Build ladder", style="Accent.TButton", command=self.build).pack(side="left", anchor="s")
        self.info = ttk.Label(self, text="", style="Muted.TLabel")
        self.info.pack(anchor="w", pady=6)
        self.table = ak.Table(self, app, [("n", "Step", 6), ("title", "Problem", 34), ("topic", "Topic", 24), ("d", "Difficulty", 10), ("chance", "Estimated chance", 15)])
        self.table.pack(fill="both", expand=True)

    def build(self):
        try:
            count, low, high = int(self.count.get()), int(self.low.get()), int(self.high.get())
        except ValueError:
            messagebox.showerror("Ladder", "Enter whole numbers.", parent=self)
            return
        skills = tr.topic_skills(attempts_full(self.app.store))
        skill = tr.overall_skill(skills)
        rows = tr.build_ladder(self.app.store.list("problem"), skill, count, (low, high))
        self.info.configure(text="Built around your skill estimate of %d. %s" % (skill, "" if rows else "Add more unsolved problems in this range."))
        self.table.fill([[i + 1, p["title"], p["topic"], p["difficulty"], "%d%%" % (100 * tr.win_probability(skills.get(p["topic"], skill), p["difficulty"]))]
                         for i, p in enumerate(rows)])

    def refresh(self):
        self.build()


class Stats(ttk.Frame):
    title = "Progress"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text="Problems solved per week, last 12 weeks", style="Muted.TLabel").pack(anchor="w")
        self.chart = tk.Canvas(self, bg=app.colors["panel"], highlightthickness=0, height=int(240 * app.scale))
        self.chart.pack(fill="x", pady=6)
        self.chart.bind("<Configure>", lambda e: self.draw())
        self.history = ak.EntityView(self, app, "attempt")
        self.history.pack(fill="both", expand=True)
        self.commit = self.history.commit

    def draw(self):
        c, col, s = self.chart, self.app.colors, self.app.scale
        c.delete("all")
        v = tr.weekly_counts(attempts_full(self.app.store), ak.today())
        w, h = max(c.winfo_width(), 200), max(c.winfo_height(), 100)
        top = max(v + [1])
        bw = (w - 40 * s) / len(v)
        for i, n in enumerate(v):
            x = 20 * s + i * bw
            bh = (h - 44 * s) * n / top
            c.create_rectangle(x + 4, h - 22 * s - bh, x + bw - 4, h - 22 * s, fill=col["accent"], outline="")
            c.create_text(x + bw / 2, h - 22 * s - bh - 9 * s, text=str(n), fill=col["ink"], font=(ak.FONT, 9))

    def refresh(self):
        self.history.refresh()
        self.draw()


class APP(ak.BaseApp):
    APP_NAME, ACCENT = "Problem Trainer", "#4338ca"
    SCHEMA, SAMPLE = SCHEMA, staticmethod(sample)
    VIEWS = [Today, Bank, Skills, Ladder, Stats, ak.DataView]


def main(argv=None):
    return ak.main(APP, argv)
