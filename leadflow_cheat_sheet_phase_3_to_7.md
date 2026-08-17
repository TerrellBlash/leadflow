# leadflow Cheat Sheet: Phases 3-7

Companion to the Phase 1-2 cheat sheet. Lookup reference, not prose. `Cmd + F` this file.

Project moved to `~/dev/leadflow` in Phase 7. Never put it back under `~/Desktop` (iCloud sync destroys virtualenvs).

---

## Session start

```bash
lf                    # alias: cd ~/dev/leadflow && source .venv/bin/activate
```

If the alias is missing or stale:

```bash
echo 'alias lf="cd ~/dev/leadflow && source .venv/bin/activate"' >> ~/.zshrc
source ~/.zshrc
```

Two tabs. Tab 1 = server. Tab 2 = everything else. Every new tab needs `lf` first.

---

## Server commands

| Want | Command |
|---|---|
| Start dev server | `python -m uvicorn main:app --reload --reload-exclude '.venv/*'` |
| Start without reload (stable) | `python -m uvicorn main:app` |
| Stop | `Ctrl + C` |
| Port already in use | `lsof -ti:8000 \| xargs kill -9` |
| Different port | add `--port 8001` |

Always `python -m uvicorn`, never bare `uvicorn`.

---

## Local URLs

| URL | What |
|---|---|
| http://localhost:8000/ | Service info |
| http://localhost:8000/health | Liveness |
| http://localhost:8000/leads | GET list, POST create |
| http://localhost:8000/workflow_runs | Execution history |
| http://localhost:8000/docs | Interactive docs |

## Live URLs

Base: `https://leadflow-ejqy.onrender.com`

Free tier sleeps after ~15 min idle. First request takes 30-60s to wake.

---

## Package management (uv)

| Want | Command |
|---|---|
| Install | `uv pip install <name>` |
| Install with extras | `uv pip install "<name>[extra]"` |
| Show one package | `uv pip show <name>` |
| List all | `uv pip list` |
| Lock versions | `uv pip freeze > requirements.txt` |
| Install from lockfile | `uv pip install -r requirements.txt` |
| Rebuild venv | `rm -rf .venv && uv venv --python 3.11 && source .venv/bin/activate && uv pip install -r requirements.txt` |

Update `requirements.txt` immediately after any install. Render builds from it.

---

## Database

### Inspect

```bash
sqlite3 leadflow.db ".tables"              # list tables
sqlite3 leadflow.db ".schema"              # all schemas
sqlite3 leadflow.db ".schema drafts"       # one table
sqlite3 leadflow.db "SELECT * FROM leads;"
sqlite3 leadflow.db "SELECT content FROM drafts;"
sqlite3 leadflow.db "SELECT * FROM workflow_runs;"
```

### Schema changes

`create_all()` creates missing tables. It never alters existing ones.

| Change | Fix |
|---|---|
| New table | Save model, restart server. Done. |
| New column on existing table | `sqlite3 leadflow.db "DROP TABLE x;"` then restart |
| Table created half-built | Same drop + restart. Cause: saved the model file mid-edit and reload fired early. |

Avoid the half-built table: finish typing the whole class, then save once. Or restart the server manually instead of relying on auto-reload.

---

## The three tables

```
leads                    workflow_runs              drafts
─────                    ─────────────              ──────
id                       id                         id
name                     lead_id      → leads.id    lead_id  → leads.id
email                    status                     content
company                  current_step               model
status                   started_at                 prompt_version
created_at               finished_at                created_at
                         error_message
```

---

## Adding a workflow step

Three edits in `orchestrator.py`:

```python
# 1. imports at top, if the step needs them

# 2. the function, ABOVE WORKFLOW_STEPS
def my_step(lead: Lead, db: Session) -> None:
    # do work
    # raise on failure

# 3. register it, in execution order
WORKFLOW_STEPS = [
    ("log_lead", log_lead),
    ("tag_priority", tag_priority),
    ("draft_outreach", draft_outreach),
    ("notify_slack", notify_slack),
    ("my_step", my_step),
]
```

`run_workflow` never changes.

**`WORKFLOW_STEPS` must be the last thing in the file.** Python evaluates it at import time; every function it names must already be defined. Putting it above a step gives `NameError: name 'x' is not defined`.

### The step contract

```python
def step_name(lead: Lead, db: Session) -> None:
```

Two args. No return. Raise on failure. The orchestrator catches it, marks the run failed, records the step name and the exception text.

---

## Secrets

| File | Contents | In git? |
|---|---|---|
| `.env` | Real values | Never |
| `.env.example` | Same keys, empty values | Yes |
| Render env vars | Production values | N/A (platform storage) |

Current keys: `ANTHROPIC_API_KEY`, `SLACK_WEBHOOK_URL`, `DATABASE_URL` (production only).

**Verify a secret never leaked:**

```bash
git log --all --full-history -- .env     # empty output = clean
git status                                # .env must not appear
```

In code:

```python
from dotenv import load_dotenv
load_dotenv()          # first lines of main.py, before other project imports

value = os.environ.get("KEY_NAME")
if not value:
    raise ValueError("KEY_NAME is not set")
```

Env var names are string matches against your code. A typo produces a runtime failure in one step, not a build failure.

---

## Anthropic API

```python
from anthropic import Anthropic

client = Anthropic(timeout=30.0)          # reads ANTHROPIC_API_KEY from env

response = client.messages.create(         # messages, plural
    model="claude-haiku-4-5-20251001",
    max_tokens=300,
    messages=[{"role": "user", "content": prompt}],
)
text = response.content[0].text            # list of blocks; [0].text for plain text
```

| Gotcha | Symptom |
|---|---|
| `client.message.create` | `AttributeError` |
| Typo in model string | 404 from API |
| `{placeholder}` not matching `.format()` kwarg | `KeyError` |
| No timeout | Request hangs indefinitely |

Prompt lives as a module constant with a `PROMPT_VERSION` string. Bump the version when the prompt changes; drafts record which version produced them.

---

## Outbound HTTP

```python
import requests

response = requests.post(url, json={"text": message}, timeout=10)
response.raise_for_status()     # raises on 4xx/5xx
```

Never omit `timeout`.

---

## Git

| Want | Command |
|---|---|
| Status | `git status` |
| Stage specific files | `git add main.py orchestrator.py` |
| Commit | `git commit -m "message"` |
| Push (triggers Render deploy) | `git push` |
| History | `git log --oneline` |
| View a commit's diff | `git show <hash>` (press `q` to exit) |
| Undo uncommitted changes to a file | `git checkout -- <file>` |
| Reverse a pushed commit | `git revert <hash>` |

Prefer naming files over `git add -A`. `-A` is how a stray 597KB image ended up in the repo.

### Recovering from an agent that edited your project

```bash
git status                             # survey what changed
git checkout -- <tracked files>        # revert modifications
rm <each new file, named>              # delete additions, no wildcards
grep -c "pattern" *.py                 # verify nothing survived
```

Works only if the last good state was committed. Commit before letting any agent touch the project.

---

## Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
```

| Line | Why |
|---|---|
| `COPY requirements.txt` before `COPY . .` | Layer caching. Code edits skip the reinstall. |
| `--host 0.0.0.0` | Without it, the container accepts nothing from outside |
| `--port $PORT` | Platform assigns the port |
| No `--reload` | Development only |

`.dockerignore` must include `.env`, `.venv/`, `.git/`, `*.db`.

### Local Docker

```bash
docker build -t leadflow .
docker run -p 8000:8000 --env-file .env -e PORT=8000 leadflow
```

---

## Render

| Task | Where |
|---|---|
| Deploy | Automatic on `git push` to main |
| Logs | Service page, Logs tab |
| Env vars | Service page, Environment tab |
| Manual redeploy | Service page, Manual Deploy |
| Database connection string | Postgres page, Connections, Internal Database URL |

Free tier is not the default on create-resource pages. Read the monthly total before clicking create.

Use Internal Database URL, not External. It only resolves between services in the same region, so the web service region must match the database region.

---

## Error lookup

| Error | Cause | Fix |
|---|---|---|
| `NameError: name 'x' is not defined` | `WORKFLOW_STEPS` above the function | Move the list to the bottom of the file |
| `SyntaxError: expected ':'` | Missing colon on a `class` or `def` | Read the line above the reported one too |
| `SyntaxError: perhaps you forgot a comma?` | Missing comma in a tuple or list | Python 3.11 names the fix |
| `IndentationError: unexpected indent` | Stray character on its own line | Check the exact line reported |
| `ModuleNotFoundError` | venv not active, or package not installed | `lf` then `uv pip install <name>` |
| `AttributeError` on SDK call | Method name typo (`message` vs `messages`) | Check the SDK docs |
| `KeyError` from `.format()` | Template placeholder not supplied | Match `{name}` to `name=` |
| `ValueError: X is not set` | Env var missing or misspelled | Check `.env` and Render env vars |
| `[Errno 48] Address already in use` | Old server still holding the port | `lsof -ti:8000 \| xargs kill -9` |
| `[Errno 89] Operation canceled` | Filesystem stalling on reads | Project is in a synced folder. Move it. |
| `KeyError: 'asyncio'` in anyio | Reload fired mid-request | `--reload-exclude '.venv/*'` or drop `--reload` |
| Import takes minutes at 0% CPU | iCloud evicting venv files | Move project out of Desktop/Documents |
| Deploy succeeds, endpoint unreachable | Missing `--host 0.0.0.0` or wrong port | Check the Dockerfile CMD |
| 500 with no detail | Code raised | Read the traceback in the server log |
| 422 | Pydantic rejected the body | Response names the failing field |

---

## Diagnosing "the last thing didn't happen"

Walk the chain in order. Each link passes or names the failure.

```
POST returned what status?          docs page
  → run created?                    GET /workflow_runs
    → which step recorded?          current_step
      → what error?                 error_message
        → what did the server log?  Tab 1 / Render logs
```

A run marked `completed` whose `current_step` is not the last step means the step was never registered.

### Reading a traceback

Bottom up. The last line is the error type and message. The line above it is your file and line number. Everything above that is framework code showing how it got there.

Syntax errors often point at the line *after* the real mistake.

### Measuring slowness

```bash
time python -c "import somelib; print('ok')"
```

High wall-clock with low CPU means blocked on I/O, not slow code.

---

## Habits

| Do | Not | Why |
|---|---|---|
| `python -m pip`, `python -m uvicorn` | bare `pip`, `uvicorn` | Anchors to the active environment |
| `uv pip install` | `pip install` | Faster, avoids pip breakage |
| `git add <files>` | `git add -A` | Prevents committing strays |
| `git status` before commit | Committing blind | Catches secrets and junk |
| Commit before running an agent | Experimenting on uncommitted work | Git is the undo |
| Finish typing, then save | Saving mid-edit | Auto-reload can snapshot a half-written model |
| Project in `~/dev/` | `~/Desktop` or `~/Documents` | iCloud sync destroys virtualenvs |
| Timeout on every network call | Omitting it | A hung call hangs the worker |

---

## Current limitations (the backlog)

In rough priority order. Each one moves from the README's Limitations section to its body when done.

1. No pytest suite
2. Workflow blocks the HTTP response (needs BackgroundTasks or a queue)
3. Prompt v1 fabricates statistics; v2 comparison not run
4. No draft evaluation
5. No token or cost tracking
6. No retries, no idempotency
7. No `GET /drafts` endpoint
8. `create_all` instead of Alembic migrations
9. No auth on the webhook
