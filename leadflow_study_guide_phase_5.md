# leadflow Study Guide: Phase 5 — The AI Step

Addendum to the Phase 1-4 study guides. Read those first if you haven't.

This one replaces any earlier "phase 5" file in the repo — that one described a self-improving agentic system that was built by mistake and reverted. This guide covers what you actually built.

---

## Part 1: What Phase 5 added

Before Phase 5: leads got validated, saved, tagged, and announced in Slack. All rule-based. Every step was deterministic — same input, same output, forever.

After Phase 5: Claude writes a personalized outreach email for each lead. The draft is stored in a new `drafts` table with metadata about which model and which prompt version produced it.

This is the phase that makes the resume claim true. Not "workflow automation" — **AI workflow automation**. An LLM doing real work inside a pipeline you built.

The email Claude wrote for the test lead:

```
Marcus,

I came across Brightpath Analytics and noticed you're working in the
analytics space where data quality often becomes a bottleneck as teams
scale. We've helped similar companies reduce their manual data validation
work by about 40% through our platform. Given your background, I thought
it might be worth a quick conversation to see if there's a fit.

What's currently your biggest pain point when it comes to data pipeline
reliability?
```

Hold onto that "40%" figure. It's the most important thing in this guide, and Part 6 explains why.

---

## Part 2: The design decision — why a separate drafts table

Three options were on the table for storing the draft:

| Option | Shape | Cost |
|---|---|---|
| A | New `draft_email` column on the leads table | Simplest; requires deleting the dev DB (create_all can't add columns) |
| B | Post to Slack, store nothing | No schema change, but the draft isn't queryable |
| C | New `drafts` table with model + prompt_version | More code; enables comparison across prompts and models |

**C was chosen deliberately.** The defensible reason, and the one to say in an interview:

> Drafts are generated artifacts with their own lifecycle. A lead might get several over time, and each one is tied to the model and prompt version that produced it — so you can compare quality when either changes.

That's the observability argument. It only holds if you can say it without flinching, which is why the reason mattered more than the choice.

A secondary practical win: C only *adds* a table, which `create_all` handles fine. Option A would have altered an existing table, which it can't — the leads and workflow_runs data would have needed deleting.

### The table

```
┌───────────────────────────────┐
│           drafts              │
├───────────────────────────────┤
│ id              (int, PK)     │
│ lead_id         (int, FK)     │  → leads.id
│ content         (str)         │  the email text
│ model           (str)         │  which Claude model
│ prompt_version  (str)         │  "v1", "v2", ...
│ created_at      (datetime)    │
└───────────────────────────────┘
```

Structurally identical patterns to `WorkflowRun` — FK to leads, lambda timestamp. The two columns doing new work are `model` and `prompt_version`. They're what turn a pile of drafts into comparable data.

---

## Part 3: The draft_outreach step

```python
PROMPT_VERSION = "v1"
DRAFT_MODEL = "claude-haiku-4-5-20251001"

OUTREACH_PROMPT = """You are writing a short cold outreach email on behalf of a B2B software company.

Lead details:
- Name: {name}
- Company: {company}
- Priority: {status}

Write a 3-4 sentence email to this person. Rules:
- Reference their company by name once, naturally
- No buzzwords, no "I hope this finds you well", no exclamation marks
- End with one specific, low-commitment question
- Output ONLY the email body. No subject line, no signature, no preamble."""


def draft_outreach(lead: Lead, db: Session) -> None:
    client = Anthropic()

    prompt = OUTREACH_PROMPT.format(
        name=lead.name,
        company=lead.company,
        status=lead.status,
    )

    response = client.messages.create(
        model=DRAFT_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    email_text = response.content[0].text

    draft = Draft(
        lead_id=lead.id,
        content=email_text,
        model=DRAFT_MODEL,
        prompt_version=PROMPT_VERSION,
    )
    db.add(draft)
    db.commit()
```

### Line by line

**`client = Anthropic()`** — no API key passed in. The SDK reads `ANTHROPIC_API_KEY` from the environment automatically, which `load_dotenv()` loaded from `.env` at startup. The key never appears in code, never reaches git. Same secrets discipline as the Slack webhook, second time paying off.

**`OUTREACH_PROMPT.format(...)`** — `.format()` substitutes `{name}`, `{company}`, `{status}` with the real values. If the template asks for a placeholder you don't supply, it raises `KeyError` at runtime (see the war stories — this bit us).

**`max_tokens=300`** — a hard ceiling on the response. Doubles as length control and cost control: a 3-4 sentence email runs ~100 tokens, so 300 is headroom without letting a confused model write an essay on your dime.

**`response.content[0].text`** — the API returns a *list* of content blocks. For a plain text request there's one block, and its `.text` is the email.

**Step order.** `draft_outreach` sits before `notify_slack` in `WORKFLOW_STEPS`, so a future version of the Slack message can include the draft. Ordering is cheap to get right now, annoying to change later.

**What did NOT change: `run_workflow`.** Third integration, zero edits to the engine. The step contract from Phase 3 has now held across a rule-based step, an HTTP integration, and an LLM call.

---

## Part 4: Prompt design as engineering

The prompt is a module-level constant, not an inline string. That's deliberate: it's versioned (`PROMPT_VERSION = "v1"`), it's diffable in git, and it sits next to the code that uses it. **The prompt is code that happens to be English.**

### Every rule kills a specific failure

Ask Claude to "write an outreach email" with no constraints and you reliably get:

```
Subject: Quick Question About Brightpath Analytics!

Hi Marcus!

I hope this email finds you well! ...
```

Plus, often, a "Certainly! Here's a draft:" preamble bolted to the front.

Map the rules to what they prevent:

| Rule | Failure it prevents |
|---|---|
| Reference their company by name once, naturally | Generic template that could go to anyone |
| No buzzwords, no "I hope this finds you well" | The spam register every recipient filters out |
| No exclamation marks | Fake enthusiasm |
| 3-4 sentences | Walls of text |
| End with one specific, low-commitment question | "Let me know!" non-endings |
| **Output ONLY the email body** | Preamble/subject/signature contaminating stored data |

That last one matters most *because of where the output goes*. We store `email_text` straight into the database. Any "Here's your email:" preamble becomes part of every saved draft, forever.

**The generalizable lesson: prompt design is mostly subtractive.** You're not describing the ideal output so much as fencing off the failure modes you've observed. Write the prompt, read the output, find what's wrong, add a rule, bump the version. That loop is the work.

### Why versioning matters

`PROMPT_VERSION` is a string you bump whenever the prompt changes. Because it's stored on every draft, you can query drafts from v1 and v2 side by side and judge whether a change helped. Without it, you'd have a pile of drafts with no way to know which prompt produced which.

---

## Part 5: Non-determinism — the thing that makes this different

Every function you'd written before this phase was deterministic. `tag_priority` given "Founder Jane" returns "hot" every single time, forever.

`draft_outreach` given the same lead returns a *different email each time*. Same input, different output. That changes three things:

**Testing.** You can't assert on exact output. You test properties instead: is it non-empty? under N characters? does it contain the company name? does it lack an exclamation mark? Those are checkable; "equals this exact string" is not.

**Logging.** With deterministic code, inputs are enough to reconstruct what happened. With an LLM you must store the *output* — which is exactly what the drafts table does.

**Promises.** You can't say "the system writes good emails." You can say "the system drafts emails for human review." The design (store, don't auto-send) follows directly from the non-determinism.

---

## Part 6: The 40% that wasn't — hallucination in your pipeline

Look again at the generated email:

> "We've helped similar companies reduce their manual data validation work by about **40%** through our platform."

Your prompt supplied exactly three facts: name, company, priority. Nothing about a platform. Nothing about other customers. Nothing about 40%.

**Claude invented it** — because cold outreach emails in its training data are full of invented-sounding statistics, so a plausible-sounding statistic is what "cold outreach email" generates.

This is hallucination, in a production pipeline, on the first draft, from a prompt that looked careful. Not an edge case. The default behavior.

### Why it matters more than the feature

Three real consequences:

1. **The human-review design was already correct.** Drafts are stored, not sent. If this auto-sent, you'd be emailing fabricated claims to strangers under a company's name. Storage-plus-review isn't caution theater; it's the load-bearing safety property.

2. **It's the strongest interview story this project produces.** The answer to "what surprised you?":

   > My first draft fabricated a 40% statistic I never supplied. That's why the system stores drafts for human review rather than auto-sending, and why prompts are versioned — so I can measure whether a change actually reduces fabrication.

   That demonstrates you treat an LLM as an unreliable component to engineer around, not as magic. Most candidates don't have that story because most tutorial projects never look closely at their own output.

3. **The fix is a prompt change, and it's testable.** Add a rule:

   ```
   - Do not invent statistics, customer counts, or product capabilities.
     You know only the lead's name and company. Do not claim results.
   ```

   Bump `PROMPT_VERSION` to `"v2"`. Generate drafts. Compare v1 and v2 in the drafts table.

   **That comparison is only possible because of the Option C decision.** The architecture choice from Part 2 pays for itself the first time you need to evaluate a prompt change.

---

## Part 7: New Python and API concepts

### The Anthropic SDK

```python
from anthropic import Anthropic

client = Anthropic()                    # reads ANTHROPIC_API_KEY from env
response = client.messages.create(      # note: messages, plural
    model="claude-haiku-4-5-20251001",
    max_tokens=300,
    messages=[{"role": "user", "content": prompt}],
)
text = response.content[0].text
```

`messages` is a list of turn dicts, each with a `role` ("user" or "assistant") and `content`. A single-turn request is one user message. Multi-turn conversations append prior turns to the list — the API is stateless, so *you* carry the history.

### Tokens and cost

Text is billed in tokens, roughly ¾ of a word each. You pay for input (your prompt) and output (the response), at different rates. A leadflow draft is maybe 150 input + 100 output tokens — a fraction of a cent on Haiku.

The habit worth building isn't miserliness, it's *knowing the number before you ship*. A loop that calls an LLM per row of a 100,000-row table is a very different bill than one call per lead.

### `.format()` and KeyError

```python
"Hello {name}".format(name="Marcus")     # works
"Hello {name}".format(person="Marcus")   # KeyError: 'name'
```

The template's placeholders and the kwargs you pass must match exactly. Mismatches only surface at runtime.

### API timeouts

Not in the current code, and it should be:

```python
client = Anthropic(timeout=30.0)
```

Same principle as `timeout=10` on the Slack call. Any network call without a timeout can hang forever. 30s because LLM calls legitimately take longer than webhook posts. Worth adding.

---

## Part 8: The war stories (Phase 5 edition)

Phase 5 produced the hardest debugging session of the project, and the lesson is bigger than any of the code.

### War story 1: the twelve-minute import

The symptom chain: POST hangs → server won't start → uvicorn crashes with `OSError: [Errno 89] Operation canceled` mid-import → WatchFiles reloading on a hundred venv files at once.

The measurement that broke it open:

```bash
time python -c "import anthropic; print('ok')"
ok
1.09s user  0.91s system  0% cpu  12:28.74 total
```

**Two seconds of CPU work spread across twelve and a half minutes at 0% CPU.** That is not slow code. That is a process blocked on I/O — asking for files and waiting.

**The cause: iCloud was syncing `~/Desktop`, and the project lived there.** Every file in the venv — thousands of them — was subject to cloud eviction and on-demand re-download. Importing one library touched hundreds of files, each potentially a round trip to Apple's servers.

**The fix:**

```bash
mkdir -p ~/dev
mv ~/Desktop/leadflow ~/dev/leadflow
cd ~/dev/leadflow
rm -rf .venv && uv venv --python 3.11 && source .venv/bin/activate
uv pip install -r requirements.txt
```

Result: `Installed 33 packages in 100ms`. Same packages that had taken minutes.

**What it retroactively explains.** Nearly every "weird" failure earlier in this project was a file operation that started and didn't finish:

- The venv created with a `bin/` but no `lib/` (Phase 2)
- pip vanishing mid-upgrade (Phase 2)
- The `drafts` table freezing half-built — twice (Phase 5)
- Random `OSError: Operation canceled` on ordinary reads

We treated each as its own bug for weeks. One root cause underneath all of them.

**The transferable lessons:**

- **Never put a development project in an iCloud/Dropbox/OneDrive-synced folder.** `~/dev/` or `~/code/`, never `~/Desktop` or `~/Documents` on a Mac with sync enabled.
- **When something is slow, measure where the time goes.** `time` separating 2s of CPU from 12min of wall clock is what turned "it's slow" into "it's blocked on I/O." A guess would never have found this.
- **Repeated unrelated-looking failures in one area usually share a cause.** Four strange bugs in one directory was a signal, and it took too long to read it.

### War story 2: WORKFLOW_STEPS ordering

```
NameError: name 'draft_outreach' is not defined
```

`WORKFLOW_STEPS` was defined *above* `draft_outreach`. Python evaluates a module-level list at import time, and it named a function seven lines before that function existed.

**Rule:** `WORKFLOW_STEPS` lives at the bottom of `orchestrator.py`, after every step function. Everything it references must be defined first.

### War story 3: three typos that each fail differently

- `claude=haiku-4-5-...` (equals instead of hyphen) → 404 from the API
- `{priority}` in the template vs `status=` in `.format()` → `KeyError`
- `client.message.create` vs `messages.create` → `AttributeError`

Three one-character-class mistakes, three completely different error types. Reading *which* exception you got is half of knowing where to look.

### War story 4: the agentic system that appeared

An open-ended question ("show me a self-improving agentic system") asked of Claude Code — running inside Cursor, therefore pointed at the leadflow workspace — resulted in ~10 new files of A/B testing and self-improvement machinery written directly into the project, on top of an unfinished Phase 5.

**The recovery, which is the useful part:**

```bash
git status                                    # survey: 6 modified, N untracked
git checkout -- <the 6 tracked files>         # revert modified files to last commit
rm <each generated file, named explicitly>    # delete new files, no wildcards
rm leadflow.db                                # rebuild schema from create_all
grep -c "draft\|Draft\|anthropic" *.py        # verify nothing survived
```

That worked for exactly one reason: **Phase 4 was committed and pushed.** Git gave a floor to fall back to. An uncommitted project has no undo.

**The lessons:**

- Agentic tools act on the directory they're pointed at. Launched from Cursor, that's your open workspace — not a neutral chat.
- Scope must be stated as a *boundary*, not a goal. "Recover my project" invites judgment calls. "Restore these files. Do not modify code, do not commit, do not push" does not.
- Keep a scratch folder for exploratory questions. Point the agent there.
- **Commit before you experiment.** `git status` clean before any agent touches the project.
- When any tool — including this one — hands you a summary of work it did, the question is: *can you explain it?* If not, it isn't yours yet.

---

## Part 9: Where Phase 5 leaves the project

**Working end to end:** a POST to `/leads` validates the payload, persists a lead, then runs four steps in order — log, tag priority by rule, generate an AI draft via Claude, notify Slack — with each step's progress and any failure recorded in `workflow_runs`, and each draft stored with its model and prompt version.

**Known limitations** (all good interview answers to "what would you improve?"):

- **No timeout on the Anthropic call.** Should be `Anthropic(timeout=30.0)`. Inconsistent with the Slack step, which does have one.
- **Workflow runs synchronously inside the POST.** The API response waits for the LLM call — a slow model call means a slow HTTP response. Fix: background tasks or a queue.
- **Prompt v1 hallucinates.** Documented in Part 6; the fix is a v2 rule plus a comparison against stored v1 drafts.
- **No draft evaluation.** Nothing scores draft quality or correlates it to real outcomes. Building a judge is possible; validating it against actual reply rates is the hard, honest part.
- **No `GET /drafts` endpoint yet.** Drafts are only readable via sqlite. A `DraftOut` schema exists, so this is a five-line addition.
- **Still `create_all`, not Alembic.** Schema changes require dropping tables. Fine for dev, wrong for production.

**Next:** Phase 6 (Google Sheets logging) or straight to Phase 7 (Docker, deploy, README, demo video). Phase 6 is a third integration demonstrating a skill Slack already demonstrates; Phase 7 is what turns this from code on a laptop into a portfolio piece. The case for skipping ahead is strong.
