# leadflow Study Guide: Phase 5 — The System That Improves Itself

Addendum to the Phase 1–4 study guides. Read those first if you haven't.

---

## Part 1: What Phase 5 added

Before Phase 5, leadflow did the same thing forever. You wrote a prompt in
Phase 4, and that prompt would still be there in ten years, producing exactly
the same quality of email.

After Phase 5, leadflow **notices when its emails are bad and writes itself a
better prompt.**

That sentence sounds like magic. It isn't. It's four boring ideas stacked:

1. Score every email you send.
2. Keep the scores in a table.
3. When the scores are bad, show the bad ones to a model and ask for a better prompt.
4. **Refuse to use the new prompt until arithmetic proves it's better.**

Step 4 is the entire trick. Steps 1–3 are what everybody builds. Step 4 is what
separates a system that improves from a system that just churns.

### The homework analogy

Imagine you get a C on an essay.

- **A system with no loop** writes the next essay exactly the same way.
- **A bad "self-improving" system** grades its own essay, gives itself an A,
  and learns nothing. This is what happens when you let a model score its own
  output.
- **A real loop** has a teacher with a rubric taped to the wall. You can read
  the rubric. You cannot edit the rubric. You try a new approach, and you only
  keep it if your grade actually goes up.

The rubric taped to the wall is `evals/rubric.md`. In this codebase it is
called an **anchor**, and `LOOP.md` says out loud that the loop may read it and
may never write it.

---

## Part 2: The one rule — the model proposes, the code disposes

Look at who does what:

| Job | Who |
|---|---|
| Write the email | a model |
| Score the email | a model |
| Rewrite the prompt | a model |
| **Decide which prompt wins** | **plain Python arithmetic** |

Three of the four jobs are done by AI. The fourth is done by `experiment.py`,
which contains no AI at all — just addition and comparison.

Why? Because a system where the model does all four will always report success.
Not because it's lying, but because "is this better?" is a judgment call, and
if the thing being judged and the judge share an interest in the answer, you
have no measurement. You have a vibe.

This connects to one of the rules in your `CLAUDE.md`:

> **Rule 5 — Use the model only for judgment calls.** If code can answer, code answers.

"Is 7.8 bigger than 7.2 plus 0.25?" is not a judgment call. It's arithmetic. So
it's arithmetic in the code.

---

## Part 3: The new files, and the Python in them

### `prompts.py` — the prompt becomes data

In Phase 4 the prompt was a string sitting inside `orchestrator.py`. A system
that rewrites its prompt can't do that — you can't rewrite a line of source
code while the program is running. So the prompt moves into the database, and
this file keeps only the *first* one plus the rules any rewrite must follow.

```python
REQUIRED_PLACEHOLDERS: tuple[str, ...] = ("{name}", "{company}", "{status}")
```

**Python concept: tuple vs list.** A list uses `[]` and can be changed. A tuple
uses `()` and cannot. This is a tuple on purpose — it's a contract. If some
other file could do `REQUIRED_PLACEHOLDERS.append(...)`, the contract wouldn't
be a contract. Python lets you say "this cannot change," and when something
shouldn't change, say so.

**Python concept: the type hint `tuple[str, ...]`.** Read it as "a tuple of
strings, any number of them." The `...` genuinely means "and so on" — it is
real Python syntax here, not a placeholder for you to fill in.

```python
def missing_placeholders(template: str) -> list[str]:
    return [p for p in REQUIRED_PLACEHOLDERS if p not in template]
```

**Python concept: list comprehension.** That one line means:

```python
result = []
for p in REQUIRED_PLACEHOLDERS:
    if p not in template:
        result.append(p)
return result
```

Same thing, five lines shorter. The shape is always
`[what_to_keep for item in collection if condition]`.

Notice what this function returns: **a list of what's missing, not True/False.**
`True`/`False` tells you something is wrong. A list tells you *what* is wrong,
which is what the error message needs. When you have the information, pass the
information.

---

### `checks.py` — the free stuff first

```python
BANNED_PHRASES: tuple[str, ...] = ("i hope this finds you well", "circle back", ...)
```

Counting words and searching for banned phrases are things a computer does
perfectly, instantly, and for **zero dollars**. Asking a language model to do
it is slower, costs money, and is occasionally wrong.

So these run first. Only if the email survives do we pay Opus to judge it.

That's not just thrift. Watch what happened when we ran the real pipeline:

```
--- CHECKS ---
failed: does not end with a question
--- VERDICT ---
score=0.0  flaw=does not end with a question
```

The model wrote a question and forgot the question mark. A regex caught it in
microseconds for free. This is the shape of good AI engineering: **make the
cheap deterministic thing the first line of defence, and the model the last.**

```python
@dataclass(frozen=True)
class CheckResult:
    passed: bool
    failures: tuple[str, ...]
```

**Python concept: `@dataclass`.** A decorator — a line starting with `@` that
sits above a definition and modifies it. `@dataclass` writes the boring parts of
a class for you: the `__init__`, the `__repr__`, the equality check. Without it
you'd hand-write:

```python
class CheckResult:
    def __init__(self, passed, failures):
        self.passed = passed
        self.failures = failures
```

`frozen=True` means once you build one, nobody can change it. A check result is
a **fact about a moment in time**. Nothing should be able to reach in later and
flip `passed` from `False` to `True`. Your global rules call this out:

> **Immutability (CRITICAL): ALWAYS create new objects, NEVER mutate existing ones.**

This is what that looks like in practice. The verdict is frozen because a
verdict that can be edited isn't a verdict.

---

### `judge.py` — teaching a model to fill in a form

Two deliberate decisions here, and both are the interesting part.

**Decision 1: the judge is a different, stronger model than the writer.**

```python
DRAFT_MODEL = "claude-haiku-4-5-20251001"   # in orchestrator.py
JUDGE_MODEL = "claude-opus-5"                # here
```

Models rate their own writing generously. It has a name — **self-preference
bias**. Same reason you don't mark your own exam. Using a stronger model as
judge also means the ceiling of what the system can recognise as "good" is
higher than the ceiling of what it can currently write, which is exactly the
gap the loop climbs.

**Decision 2: the judge fills in a form, not a paragraph.**

```python
class Verdict(BaseModel):
    score: float = Field(description="0 to 10. Be strict.")
    critique: str = Field(description="One sentence explaining the score.")
    worst_flaw: str = Field(description="The single biggest problem.")
```

You already met `BaseModel` in Phase 2 — Pydantic, for validating incoming
webhooks. Same tool, pointed the other way. In Phase 2 it validated data coming
*in from the internet*. Here it validates data coming *back from a model*.

This is the same lesson twice: **anything from outside your program is
untrusted until it's validated.** A model's reply is outside your program.

Then:

```python
response = client.messages.parse(..., output_format=Verdict)
return response.parsed_output      # already a real Verdict object
```

`messages.parse` sends your schema to the API, which *forces* the reply to
match it. You get back an object with `.score` as an actual float. No
`json.loads`, no praying the model remembered the closing brace.

Compare to what you'd otherwise write:

```python
text = response.content[0].text
data = json.loads(text)        # crashes if the model added "Here's the JSON:"
score = float(data["score"])   # crashes if it wrote "8/10" instead of 8
```

**Python concept: guard clauses.** Look at the order of the function body:

```python
if not checks.passed:
    return Verdict(score=0.0, ...)     # leave early
...
if response.stop_reason == "refusal":
    return Verdict(score=0.0, ...)     # leave early
...
if response.parsed_output is None:
    raise RuntimeError(...)            # leave loudly
return response.parsed_output          # the real work, un-indented
```

Handle the weird cases first and `return` out of them. The normal path ends up
at the bottom with no indentation. The alternative is a pyramid of nested
`if/else` that gets unreadable at four levels deep — which your global rules
ban outright ("No deep nesting (>4 levels)").

**Why the `None` check raises instead of returning zero.** If the API reply gets
cut off mid-form, `parsed_output` is `None`. Returning `0.0` there would look
like "the email was bad." It wasn't — we just don't know. That fake zero would
be written to the database and quietly drag down the average of whatever prompt
happened to be running, and you'd never find out why. Your rules:

> **Rule 12 — Fail loud.** Default to surfacing uncertainty, not hiding it.

A crash you can see beats a wrong number you can't.

---

### `reflector.py` — the only place a model changes the system

This is the actual self-improvement. It reads the worst-scoring emails plus the
judge's critiques, and writes a new prompt.

The important part isn't the prompt engineering. It's the **guardrails after
the model replies**:

```python
missing = prompts.missing_placeholders(rewrite.template)
if missing:
    raise ReflectionRejected(f"Rewrite dropped required placeholders: {missing}")

if rewrite.template.strip() == current_template.strip():
    raise ReflectionRejected("Rewrite is identical to the current prompt.")
```

If the model wrote a beautiful prompt that forgot `{company}`, every future
email would crash at `.format()`. So it never reaches the database.

**Python concept: custom exceptions.**

```python
class ReflectionRejected(Exception):
    """Raised when a proposed rewrite breaks the placeholder contract."""
```

That's a whole class — you inherit from `Exception` and you're done; the
docstring is the body. Why not just `raise Exception("bad rewrite")`? Because
the caller can then be specific:

```python
try:
    rewrite = reflector.propose_rewrite(...)
except reflector.ReflectionRejected as exc:
    return f"rewrite rejected: {exc}"     # expected, recoverable, carry on
```

Catching bare `Exception` would also swallow network failures, bugs, and typos
— things you want to know about. A named exception lets you catch *exactly* the
failure you planned for and let everything else surface.

---

### `experiment.py` — the referee, with no AI in it

This file decides who wins. Read the whole thing; there is nothing clever in it,
and that's the point.

```python
MIN_SAMPLES = 10
MIN_DELTA = 0.25
```

**Why `MIN_SAMPLES`.** If a new prompt writes three emails and averages 9/10,
that's luck, not skill. Flip three coins and you'll sometimes get three heads.
You need enough tries before the average means anything.

**Why `MIN_DELTA`.** Scores wobble. If the challenger gets 7.51 and the champion
7.50, promoting is superstition — you're chasing noise. Demanding a real margin
is the difference between a loop that climbs and a loop that wanders.

Now the piece most people get wrong:

```python
if lead_id % CHALLENGER_EVERY == 0:
    return challenger
return champion
```

**Python concept: `%` is modulo — the remainder after division.** `7 % 2` is 1.
`8 % 2` is 0. So even-numbered leads go to the challenger and odd to the
champion.

**Why not `random.choice()`?** Because if the workflow crashes on lead 42 and
you retry it, `random` might send it to the *other* prompt. Now lead 42 has two
drafts from two different prompts, and your comparison is quietly corrupted.
With `%`, lead 42 goes to the same side every single time, forever. Deterministic
means repeatable, and repeatable means you can trust the number.

This is Rule 5 again: routing is not a judgment call. Code answers.

```python
def score_stats(db: Session, prompt_version_id: int) -> tuple[float | None, int]:
```

**Python concept: `float | None`.** The `|` means "or". This returns a float
*or* nothing — because a prompt nobody has scored yet has no average, and `0.0`
would be a lie (that means "scored zero"). `None` means "no data." Different
things, and mixing them up is how dashboards end up wrong.

**Python concept: returning a tuple.** `return (mean, count)` hands back two
values at once, unpacked by the caller as `mean, count = score_stats(...)`.

---

### `improve.py` — the loop itself

```
1. MEASURE  - score everything unscored
2. DECIDE   - promote or retire the challenger
3. REFLECT  - write a new candidate and gate it
```

**The order is not arbitrary.** Reflect before measure and you'd rewrite the
prompt based on stale evidence, ignoring drafts that arrived since last time.
Decide before measure and you'd judge the challenger on fewer samples than you
actually have — possibly retiring a prompt that was winning.

```python
scored_ids = {row[0] for row in db.query(Evaluation.draft_id).all()}
pending = [d for d in db.query(Draft).all() if d.id not in scored_ids]
```

**Python concept: a set comprehension.** Curly braces `{}` instead of square
`[]` builds a **set** — an unordered bag of unique things.

Why a set and not a list? Because of the next line, `if d.id not in scored_ids`.
Checking `in` on a list means walking every element one at a time. Checking `in`
on a set is instant, no matter how big the set is. With 10 drafts you'd never
notice. With 100,000 the list version takes minutes and the set version doesn't.

**Rule of thumb: if you're going to ask "is this in there?" repeatedly, make it
a set.**

---

## Part 4: The anchor — the most important idea here

`LOOP.md` and everything in `evals/` are **anchors**. The loop reads them and
never writes them.

Here's the failure this prevents. Give a system the ability to change both its
work *and* the test of its work, and it will score 100% almost immediately — by
making the test easier. Not maliciously. It's just the shortest path to a high
score, and optimisers find short paths.

So the golden set and the rubric are files on disk that only a human edits. Your
global rules already state this:

> Anchors (LOOP.md criteria, eval sets) live OUTSIDE what any loop or graph may edit.

### The golden set is a set of traps

Look at `evals/golden_set.json`. These aren't nice cases:

| Case | The trap |
|---|---|
| `Founder Dave` | The "name" is a job title. Does the email say "Hi Founder"? |
| `Raman & Raman LLP` for `Priya Raman` | Her surname is in the company name. Awkward repetition? |
| `AI Synergy Cloud Solutions Inc.` | The company name is buzzword soup. Does the email echo it back? |
| `Ferretería Santos` | Non-English name. Does the email switch languages or mangle it? |

A test suite full of easy cases tells you nothing. **Every case in a golden set
should be one you're a bit worried about**, which is also your Rule 9: tests
encode *why* behaviour matters, not just what it does.

---

## Part 5: Building the rubric was harder than building the loop

This part is real and it happened while writing this phase. It's the most
useful thing in this guide.

The first rubric said two things:

- Criterion 1: full marks need a reference that "carries meaning"
- Automatic zero: inventing a fact about the company

Both sound sensible. Now run it. Here's what the judge actually returned:

```
score=0.0
critique=The only lead detail supplied is the company name, so the claim that
Northwind opened a third depot this quarter is an invented fact...
```

The prompt only supplies **name, company, status** — no facts about the company.
So any *specific* email must invent something, and any *honest* email is
generic. Every email is capped near zero, and the loop has nowhere to climb.

**The rubric was internally contradictory. Nothing could pass it.**

So the wording was fixed to reward being specific *without* inventing. Re-run:

```
honest-specific    score= 1.0
generic            score= 1.0
```

Still broken — but broken a different way. Now everything scores 1.0. The
automatic-zero rule was catching hedged inference ("I came across you while
looking at freight operators") as if it were fabrication.

**A rubric that gives everything the same score measures nothing.** A flat
rubric is exactly as useless as an impossible one — the loop can't tell which
direction is up either way.

Third attempt: scope the auto-zero to **checkable facts** — things with a truth
value the reader could dispute. A number, a date, a funding round, a headcount.
Explicitly *not* an auto-zero: hedged framing that claims nothing.

```
honest-specific    score= 8.0  flaw=Specificity is thin
generic            score= 1.0  flaw=Generic boilerplate
fabricated         score= 0.0  flaw=Fabricated checkable facts
```

Now it discriminates. 8 / 1 / 0. **That** is a working eval.

### What to take from this

Three things, and they're worth more than the code:

1. **Writing the eval is the hard part.** The loop was maybe 400 lines and
   worked first try. The rubric took three attempts and only converged because
   it was tested against deliberately different examples.

2. **You cannot tell a rubric is broken by reading it.** All three versions read
   fine. Only running them on a good email, a bad email, and a fabricated email
   exposed the problem. Your Rule 13 covers this: *reproduce, then fix*.

3. **A broken rubric fails in two directions.** Too strict → everything scores
   0. Too flat → everything scores the same. Both leave the loop with no signal.
   Always sanity-check your scorer against examples you *know* should differ, or
   you'll spend real money optimising against a number that means nothing.

Note who fixed it: **a human.** The loop cannot repair its own rubric, by
design. When the numbers stop moving, that's a signal for you to look at the
measurement — not for the machine to try harder.

---

## Part 6: How this makes money

Four routes, roughly in order of how fast you could start.

**1. Sell the outcome, not the software.** Run outreach as a service. You keep
the loop, the client gets replies. The self-improvement is your margin: your
cost per email is flat while your reply rate climbs. Nobody else in the inbox
has a system that gets better every week.

**2. Sell it as a product.** A shared SQLite file becomes one database per
tenant. The `/scoreboard` endpoint becomes the dashboard — and "watch your
prompts get better" is a genuinely good demo, because the version history shows
receipts: what changed, what it scored, whether it won.

**3. Sell the loop, not the emails.** The interesting asset here isn't outreach.
Swap the rubric and the golden set, and the same machinery improves support
replies, product descriptions, or sales-call summaries. `improve.py` doesn't
know or care that it's working on emails. That's what makes it a platform.

**4. It gets you hired.** Plenty of people can call an LLM API. Very few can
explain why the judge must be a different model than the writer, why the
promotion rule is arithmetic instead of AI, and why the rubric lives in a file
the loop can't touch. This repo is a conversation you can have in an interview,
with code behind every claim — and a README that admits what's still missing,
which is itself a signal.

---

## Part 7: What's deliberately unfinished

Not gaps in the guide — real gaps in the code, listed honestly in the README
too. Saying so is part of the work.

**The judge has never been checked against reality.** The `outcomes` table
records whether a lead actually replied. Nothing yet correlates judge score
against reply rate. Until that runs, the loop is optimising an opinion. That's
the single most valuable thing left to build, and it's the one that would prove
any of this works.

**`MIN_SAMPLES = 10` is not statistics.** Ten samples is enough to see the loop
move, not enough to be confident. A real system needs a significance test.

**No tests.** Your rules say 80% coverage. `checks.py` and `experiment.py` are
pure functions with no API calls — they're the easy, obvious place to start.

**No migrations.** Adding a column to `models.py` doesn't change an existing
SQLite file; `create_all` only creates tables that don't exist. That's why
Phase 5 needed two hand-written `ALTER TABLE` statements. Alembic exists to
solve this and should go in before the schema changes again.

---

## Part 8: Cheat sheet

| File | Job | Any AI? |
|---|---|---|
| `prompts.py` | Seed prompt + placeholder contract | No |
| `checks.py` | Free deterministic rejects | No |
| `judge.py` | Score an email against the rubric | Yes — Opus 5 |
| `reflector.py` | Write a better prompt from failures | Yes — Opus 5 |
| `experiment.py` | Decide which prompt wins | **No — never** |
| `improve.py` | Run measure → decide → reflect | Orchestrates |
| `evals/` | The frozen standard | **Anchor — humans only** |
| `LOOP.md` | The rules of the loop | **Anchor — humans only** |

| Python idea | Where | One line |
|---|---|---|
| tuple vs list | `prompts.py` | `()` can't change, `[]` can |
| list comprehension | `prompts.py` | `[x for x in y if z]` |
| `@dataclass(frozen=True)` | `checks.py` | A value object nobody can edit |
| Pydantic `BaseModel` | `judge.py` | Validate anything from outside |
| guard clauses | `judge.py` | Handle weird cases first, return early |
| custom exceptions | `reflector.py` | Catch the failure you planned for |
| `%` modulo | `experiment.py` | Deterministic split, survives retries |
| `float \| None` | `experiment.py` | "No data" is not the same as zero |
| set comprehension | `improve.py` | `{}` for fast repeated `in` checks |

| Idea | One line |
|---|---|
| Model proposes, code disposes | AI suggests; arithmetic decides |
| Anchor | The standard the loop may read and never write |
| Champion / challenger | Old vs new, split traffic, best number wins |
| Golden set | Fixed hard cases; a gate, not a benchmark |
| Self-preference bias | Models like their own writing — never let one grade itself |
| Cheap checks first | Never pay a model to count words |
