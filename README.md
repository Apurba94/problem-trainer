# Problem Trainer

A training plan that adapts to you. Keep your own bank of problems from any site, log each attempt, and the program
tracks your skill by topic, decides what to review and when, and tells you what to study next.

* **Skill by topic:** an Elo-style rating for each of 30 topics, updated from every attempt. A solve with hints counts
  for less, and a failure on an easy problem costs more.
* **Syllabus:** 30 topics from implementation to FFT, with prerequisites, so you see what is unlocked and what is blocking
  you.
* **Spaced repetition:** Leitner boxes bring problems back after 1, 3, 7, 14, 30 and 60 days. Fail one and it returns tomorrow.
* **Ladders:** a generated climb of unsolved problems around your level, mixing topics and estimating your chance on each.
* **Today:** reviews due, your streak and plain advice, such as pick harder problems or stop opening hints so soon.
* **Import:** CSV of `title,topic,difficulty,url`.

The bank starts empty apart from what you add. `--demo` opens a temporary database with fictional sample problems.

## From source

```bash
python -m problem_trainer
python -m unittest discover -s tests -t .
python build_exe.py
```

## Limits

The skill number is a motivating estimate from your own log, not an official rating. Problems are ones you add yourself:
the program does not download anything.

## License

MIT
