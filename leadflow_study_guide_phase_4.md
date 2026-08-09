# leadflow Study Guide: Phase 4 — The Slack Step

Addendum to the Phase 1-3 study guides. Read those first if you haven't.

---

## Part 1: What Phase 4 added

Before Phase 4: leads got validated, saved, and tagged — all inside your laptop. The system talked to itself.

After Phase 4: when a lead arrives, a message appears in a Slack channel a human watches. Your server now **acts on the outside world**.

The line in #leads that proves it:

```
New hot lead: Founder Jane from Startup Co (jane@startup.co)
```

Two new engineering skills came with it: **outbound HTTP** (your server as a client, not just a server) and **secrets management** (the `.env` pattern). Both get reused in every phase from here on.

### The mail carrier analogy

Until now, your server was a mailbox: things got dropped in, it stored them. Phase 4 gave it a mail carrier: now it also sends letters out. Same postal system (HTTP), opposite direction.

---

## Part 2: How Slack incoming webhooks work

Slack hands you a unique URL. POST JSON to it, a message appears in a channel:

```
your server ──POST {"text": "New lead!"}──▶ https://hooks.slack.com/services/T.../B.../xxx
                                                        │
                                                        ▼
                                              #leads: "New lead!"
```

No password. No token dance. **The URL itself is the credential.** Anyone holding it can post to your channel. That's why it lives in `.env` and nowhere else — not code, not git, not chat logs, not screenshots.

---

## Part 3: Secrets management — the .env pattern

Three files, three jobs:

| File | Contains | Committed to git? |
|---|---|---|
| `.env` | Real secrets (`SLACK_WEBHOOK_URL=https://hooks.slack.com/...`) | **NEVER** |
| `.env.example` | The same variable names with empty values | Yes |
| `.gitignore` | The line `.env` that keeps the first file invisible | Yes |

### Why the split

`.env` is your actual keys. `.env.example` is the documentation: anyone cloning the repo sees exactly which secrets they need to supply, without ever seeing yours. The `.gitignore` entry is the lock on the door.

### The verification ritual (do this every time you add a secret)

```bash
git status
```

The secret file must NOT appear. If `.env` ever shows up as untracked, stop — fix `.gitignore` before doing anything else. A key pushed to GitHub is compromised the moment it lands; bots scan every public commit for credentials within seconds. Deleting the commit later does not un-leak it.

### Loading secrets into Python

Two pieces:

**1. `load_dotenv()` — first lines of main.py:**

```python
from dotenv import load_dotenv

load_dotenv()

# ...all other imports below...
```

`load_dotenv()` reads `.env` and puts each line into the process's environment variables.

**Why it must run before the other project imports:** our current code reads the env var at call time (safe either way), but a future module might read one at import time (`API_KEY = os.environ["..."]` at the top of a file). If that module is imported before `load_dotenv()` runs, the variable is missing and the bug appears months later, nowhere near its cause. The convention "dotenv first" means you never have to think about this.

**2. `os.environ.get()` — wherever the secret is used:**

```python
webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
if not webhook_url:
    raise ValueError("SLACK_WEBHOOK_URL is not set")
```

`.get()` returns `None` if the variable is missing instead of crashing. We check and raise a *clear* error ourselves — a missing secret should fail loudly with a message that names the problem, not vanish into a mystery `None` three functions later.

---

## Part 4: The notify_slack step

```python
def notify_slack(lead: Lead, db: Session) -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("SLACK_WEBHOOK_URL is not set")

    message = f"New {lead.status} lead: {lead.name} from {lead.company} ({lead.email})"
    response = requests.post(webhook_url, json={"text": message}, timeout=10)
    response.raise_for_status()
```

And the one-line registration:

```python
WORKFLOW_STEPS = [
    ("log_lead", log_lead),
    ("tag_priority", tag_priority),
    ("notify_slack", notify_slack),
]
```

### Line by line

**`requests.post(url, json={...}, timeout=10)`**

The `requests` library is Python's standard tool for outbound HTTP. Three arguments doing three jobs:

- The URL: where to send it
- `json={"text": message}`: takes a Python dict, serializes it to JSON, sets the `Content-Type: application/json` header. One argument, three chores handled.
- `timeout=10`: give up after 10 seconds. **Never make a network call without a timeout.** Without one, a hung external service hangs your workflow forever — the request just waits. With it, a slow Slack becomes a raised exception, which becomes a failed run with a recorded error. Failure you can see beats failure that hangs.

**`response.raise_for_status()`**

If Slack answered with an error code (4xx/5xx), raise an exception. Otherwise do nothing.

This one line is where Phase 3 pays off. The exception → caught by the orchestrator → run marked "failed" → error message recorded → visible at /workflow_runs. Complete failure handling for a new integration, cost: one line. That's what the step contract bought.

**What did NOT change: `run_workflow`.** Zero edits to the engine. The Phase 3 claim — "adding integrations means writing a function and appending a tuple" — tested and true.

### Why "hot" in the Slack message matters

The message said `New hot lead` — but the POST body never contained "hot". `tag_priority` (step 2) set `lead.status = "hot"` because the name contained "founder"; `notify_slack` (step 3) read that status when building the message. The message content itself proves the steps ran **in order, sharing state**. That's the difference between a workflow and three unrelated scripts.

---

## Part 5: New Python concepts in Phase 4

### Environment variables

A key-value store attached to every running process, supplied by the operating system. Python reads them via `os.environ`. They're how configuration and secrets reach code without living in code. `load_dotenv()` is just a convenience that copies `.env` lines into that store at startup.

### os.environ.get() vs os.environ[]

```python
os.environ["MISSING"]      # raises KeyError immediately
os.environ.get("MISSING")  # returns None, your code decides what to do
```

Same dictionary-access distinction as any Python dict. For secrets, `.get()` plus an explicit check gives you the friendlier error message.

### The requests library

```python
import requests

response = requests.post(url, json=payload, timeout=10)
response.status_code       # 200, 404, 500...
response.raise_for_status()  # raise if 4xx/5xx
response.json()            # parse a JSON response body (not needed for Slack)
```

The de facto standard for HTTP in Python. FastAPI receives requests; `requests` sends them. (Async alternative: `httpx` — same API, needed if you ever make calls inside async functions. Not yet.)

### Shell aliases (the `lf` shortcut)

```bash
echo 'alias lf="cd ~/Desktop/leadflow && source .venv/bin/activate"' >> ~/.zshrc
source ~/.zshrc
```

`~/.zshrc` runs every time a Terminal opens. An `alias` defines a shorthand command. Now `lf` in any fresh Terminal = project folder + venv active. Real engineers accumulate these; the pros' dotfiles are full of them.

---

## Part 6: The war stories (Phase 4 edition)

### War story 1: the function that wasn't there

Symptom: POST succeeded, run said "completed" — but no Slack message. The tell was in the run row:

```
"status": "completed", "current_step": "tag_priority"
```

Completed, but the LAST step recorded was tag_priority. The orchestrator never saw a third step, because `notify_slack` had never actually been added to the file. The edit was discussed but not made.

**Lesson 1:** state tables don't just catch failures — they catch *absences*. "Completed after two steps" is different data than "completed after three," and reading it closely found the bug without any debugging.

**Lesson 2:** "done" should mean verified-on-disk, not remembered-as-done. The check is cheap: open the file, look.

### War story 2: the missing comma

```
("notify_slack" notify_slack),
SyntaxError: invalid syntax. Perhaps you forgot a comma?
```

A tuple needs a comma between its elements. Python 3.11+ literally suggested the fix in the error message — modern Python error messages are worth reading to the last word. Fixed without help, which is the milestone worth noting.

### War story 3: the ten-day-old Hello World

Looking at #leads for the new message, the only thing there was "Hello, World!" from the original curl test days earlier. Easy to misread stale evidence as fresh. **Check timestamps when verifying.** "A message exists in the channel" and "THE message I just triggered exists" are different claims.

---

## Part 7: The debugging pattern that solved everything

Phase 4's bug was found by walking the chain in order:

```
POST succeeded? (docs page status code)
  → run created? (/workflow_runs)
    → which step did it record? (current_step)
      → what error, if any? (error_message)
        → what did the server print? (Tab 1)
```

Each link either passes or names the failure. No guessing. This is the generic recipe for "the thing at the end didn't happen" bugs in any pipeline, and it's reusable on every phase after this one.

---

## Part 8: Where this goes next

Phase 5 applies the exact same pattern with a bigger payoff: an `ANTHROPIC_API_KEY` line in `.env`, a `draft_outreach` step that calls Claude's API to write a personalized email for each lead, one more tuple in `WORKFLOW_STEPS`. Same contract, same secrets pattern, same failure handling for free.

New concerns Phase 5 introduces that Phase 4 didn't have: API costs (each call bills tokens), rate limits, and prompt design. The mechanics stay identical; the judgment gets more interesting.
