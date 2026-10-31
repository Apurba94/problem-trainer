"""Training logic: syllabus, skill ratings by topic, Leitner review boxes, ladders, streaks and weak-area advice."""
import datetime
import random

# name: (level, prerequisites, what to learn)
SYLLABUS = {
    "Implementation": (800, [], "Read input fast, simulate carefully, test edge cases such as n = 1."),
    "Math basics": (900, ["Implementation"], "Parity, divisibility, gcd, floor and ceiling arithmetic, overflow."),
    "Sorting": (900, ["Implementation"], "Custom comparators and sorting as a first step that exposes structure."),
    "Greedy": (1000, ["Sorting"], "Exchange arguments: show that a swap towards your choice is never worse."),
    "Two pointers": (1100, ["Sorting"], "When moving one end only ever helps, a linear scan replaces nested loops."),
    "Prefix sums": (1100, ["Implementation"], "Range sums in O(1), difference arrays, and 2D prefix sums."),
    "Binary search": (1200, ["Sorting"], "Search on the answer whenever feasibility is monotone."),
    "Bit manipulation": (1200, ["Math basics"], "Masks, xor properties, and treating each bit separately."),
    "Hashing and maps": (1200, ["Implementation"], "Counting, complements, and anti-hash awareness."),
    "Basic DP": (1400, ["Prefix sums"], "State, transition, base case, order of evaluation."),
    "Graph traversal": (1400, ["Implementation"], "BFS, DFS, components, grids as graphs."),
    "Number theory": (1500, ["Math basics"], "Sieve, modular inverses, fast powers, factorisation."),
    "Stacks and deques": (1500, ["Two pointers"], "Monotonic stacks, next greater element, sliding window extremes."),
    "Shortest paths": (1600, ["Graph traversal"], "Dijkstra, Bellman-Ford, 0-1 BFS, Floyd-Warshall."),
    "Disjoint sets": (1600, ["Graph traversal"], "Union-find, offline connectivity, Kruskal."),
    "Knapsack and subset DP": (1600, ["Basic DP"], "Bounded and unbounded knapsack, subset sum."),
    "Trees": (1700, ["Graph traversal"], "Rooting, subtree sizes, diameter, tree DP."),
    "Combinatorics": (1700, ["Number theory"], "Counting with factorials, stars and bars, inclusion-exclusion."),
    "Segment trees": (1800, ["Binary search", "Prefix sums"], "Point update and range query, lazy propagation."),
    "Strings": (1800, ["Hashing and maps"], "KMP, Z, tries, polynomial hashing."),
    "Bitmask DP": (1900, ["Basic DP", "Bit manipulation"], "Subsets as states for n up to about 20."),
    "Topological order and DAG DP": (1900, ["Graph traversal", "Basic DP"], "Longest paths and counting on DAGs."),
    "Interval DP": (2000, ["Basic DP"], "Ranges as states, filled by increasing length."),
    "LCA and tree queries": (2000, ["Trees"], "Binary lifting, Euler tours, distance on trees."),
    "Game theory": (2100, ["Bit manipulation", "Basic DP"], "Win and lose states, Sprague-Grundy."),
    "Max flow and matching": (2200, ["Shortest paths"], "Modelling as flow, min cut, bipartite matching."),
    "Computational geometry": (2200, ["Math basics"], "Cross products, convex hull, exact arithmetic."),
    "Advanced DP optimisation": (2400, ["Knapsack and subset DP", "Segment trees"], "Convex hull trick, divide and conquer optimisation."),
    "Heavy-light and centroid": (2500, ["LCA and tree queries", "Segment trees"], "Path queries by decomposition."),
    "FFT and polynomials": (2600, ["Number theory"], "Convolution and NTT."),
}
TOPICS = list(SYLLABUS)
BOXES = [1, 3, 7, 14, 30, 60]
START_SKILL = 1000.0


def win_probability(skill, difficulty):
    return 1.0 / (1.0 + 10 ** ((difficulty - skill) / 400.0))


def update_skill(skill, difficulty, solved, hints=0, k=48.0):
    """Elo step. A hint counts as a partial solve, so learning with help still moves you up, but less."""
    score = (0.5 if hints else 1.0) if solved else 0.0
    return skill + k * (score - win_probability(skill, difficulty))


def topic_skills(attempts):
    """{topic: skill}, replaying attempts in date order. Attempts: dicts with topic, difficulty, solved, hints, day."""
    skills = {}
    for a in sorted(attempts, key=lambda x: (x["day"], x.get("id", 0))):
        if not a.get("topic") or not a.get("difficulty"):
            continue
        s = skills.get(a["topic"], START_SKILL)
        skills[a["topic"]] = update_skill(s, a["difficulty"], a["solved"], a.get("hints") or 0)
    return skills


def overall_skill(skills):
    """Weighted towards your strongest areas, as contest performance is."""
    if not skills:
        return START_SKILL
    top = sorted(skills.values(), reverse=True)[:8]
    return sum(top) / len(top)


def mastery(topic, skills):
    """0..1: progress towards two hundred above the topic's level. A topic never practised scores zero."""
    if topic not in skills:
        return 0.0
    level = SYLLABUS[topic][0]
    return max(0.0, min(1.0, (skills[topic] - 700.0) / max(1.0, level + 200.0 - 700.0)))


def unlocked(topic, skills):
    return all(mastery(p, skills) >= 0.6 for p in SYLLABUS[topic][1])


def next_topics(skills, count=5):
    """Unlocked topics that are not mastered yet, easiest gap first."""
    out = [t for t in TOPICS if unlocked(t, skills) and mastery(t, skills) < 0.85]
    return sorted(out, key=lambda t: (SYLLABUS[t][0], mastery(t, skills)))[:count]


def blocked_by(topic, skills):
    return [p for p in SYLLABUS[topic][1] if mastery(p, skills) < 0.6]


# ---------------- spaced repetition ----------------
def next_box(box, solved, hints=0):
    if not solved:
        return 0
    if hints:
        return box
    return min(box + 1, len(BOXES) - 1)


def add_days(day, n):
    return (datetime.date.fromisoformat(day) + datetime.timedelta(days=n)).isoformat()


def schedule_after(box, solved, hints, day):
    """(new box, next review date). Solved problems in the top box retire with no review date."""
    if solved and not hints and box == len(BOXES) - 1:
        return box, None
    b = next_box(box, solved, hints)
    return b, add_days(day, BOXES[b])


def due(problems, day):
    """Problems whose review date has arrived, oldest first."""
    return sorted((p for p in problems if p.get("review_on") and p["review_on"] <= day), key=lambda p: (p["review_on"], p.get("difficulty") or 0))


# ---------------- ladders ----------------
def build_ladder(problems, skill, count=10, spread=(-100, 300), topics=None, seed=None):
    """Unsolved problems rising in difficulty around your skill, avoiding runs of the same topic."""
    rng = random.Random(seed)
    lo, hi = skill + spread[0], skill + spread[1]
    pool = [p for p in problems if not p.get("solved") and p.get("difficulty") and lo <= p["difficulty"] <= hi and (not topics or p.get("topic") in topics)]
    rng.shuffle(pool)
    pool.sort(key=lambda p: p["difficulty"])
    if len(pool) <= count:
        chosen = pool
    else:
        chosen = [pool[i * len(pool) // count] for i in range(count)]
    out = []
    rest = list(chosen)
    while rest:
        pick = next((p for p in rest if not out or p.get("topic") != out[-1].get("topic")), rest[0])
        rest.remove(pick)
        out.append(pick)
    return out


def streaks(days, today):
    """(current, longest) streak of active days. The current one may end today or yesterday."""
    ds = sorted({datetime.date.fromisoformat(d) for d in days})
    if not ds:
        return 0, 0
    longest = run = 1
    for a, b in zip(ds, ds[1:]):
        run = run + 1 if (b - a).days == 1 else 1
        longest = max(longest, run)
    t = datetime.date.fromisoformat(today)
    cur = t if t in ds else t - datetime.timedelta(days=1)
    n = 0
    s = set(ds)
    while cur in s:
        n += 1
        cur -= datetime.timedelta(days=1)
    return n, longest


def weekly_counts(attempts, today, weeks=12):
    t = datetime.date.fromisoformat(today)
    start = t - datetime.timedelta(days=t.weekday() + 7 * (weeks - 1))
    out = [0] * weeks
    for a in attempts:
        if a["solved"]:
            d = datetime.date.fromisoformat(a["day"])
            i = (d - start).days // 7
            if 0 <= i < weeks:
                out[i] += 1
    return out


def advice(attempts, skills, today):
    """Plain sentences about what to change."""
    out = []
    recent = [a for a in attempts if a["day"] >= add_days(today, -30)]
    if not recent:
        return ["No attempts in the last 30 days. Start with one problem a day."]
    rate = sum(1 for a in recent if a["solved"]) / len(recent)
    if rate > 0.85:
        out.append("You solve %.0f%% of what you try: pick harder problems so that you keep learning." % (100 * rate))
    elif rate < 0.4:
        out.append("You solve %.0f%% of what you try: step down in difficulty, or read the idea after 40 minutes." % (100 * rate))
    hints = sum(1 for a in recent if a.get("hints"))
    if hints > len(recent) * 0.6:
        out.append("Most recent solves used hints. Try to wait longer before opening them.")
    topics = {a.get("topic") for a in recent}
    if len(topics) == 1:
        out.append("All recent work is on one topic. Mix topics, since contests do not tell you the category.")
    weak = sorted((t for t in skills if mastery(t, skills) < 0.4), key=lambda t: skills[t])[:3]
    if weak:
        out.append("Weakest practised topics: %s." % ", ".join(weak))
    return out or ["A good balance of difficulty and topics. Keep going."]


def parse_csv_rows(text):
    """title,topic,difficulty,url lines (header optional) -> dicts."""
    import csv
    import io
    rows = []
    for r in csv.reader(io.StringIO(text)):
        if len(r) < 3 or r[0].strip().lower() == "title":
            continue
        try:
            d = int(float(r[2]))
        except ValueError:
            raise ValueError("difficulty must be a number: %r" % r[2])
        rows.append({"title": r[0].strip(), "topic": r[1].strip(), "difficulty": d, "url": r[3].strip() if len(r) > 3 else ""})
    return rows
