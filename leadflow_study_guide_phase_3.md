# leadflow Study Guide: Phase 3 — The Orchestrator

Addendum to the Phase 1 + 2 study guide. Read that first if you haven't.

---

## Part 1: What Phase 3 added

Before Phase 3: a lead arrives, gets validated, gets saved. Nothing else happens.

After Phase 3: a lead arrives, gets saved, and then a **sequence of steps runs against it**. Each step's progress and outcome is recorded in a new `workflow_runs` table, visible through a new `GET /workflow_runs` endpoint.

That's the difference between a database and a workflow system.

### The assembly line analogy

A car body enters the factory. It moves through stations: paint, wheels, engine, inspection. Each station does one job. The factory tracks which station each car is at. If station 3 breaks, the car is marked "stuck at station 3" instead of the whole factory burning down.

- The **orchestrator** (`run_workflow`) is the conveyor belt.
- The **steps** (`log_lead`, `tag_priority`) are the stations.
- The **workflow_runs table** is the clipboard tracking each car's progress.

---

## Part 2: The step contract

Every step is a Python function with this exact shape:

```python
def step_name(lead: Lead, db: Session) -> None:
    # do something
    # raise an exception if it failed
```

Three rules:
1. Takes exactly two arguments: the lead and the database session.
2. Returns nothing. Steps do work (side effects), they don't compute answers.
3. Raises an exception on failure. The orchestrator catches it.

Why this matters: because every step has the same shape, the orchestrator never needs to change when you add steps. Slack in Phase 4? New function, same shape. Email drafting in Phase 5? Same shape. The engine is finished; only the station list grows.

---

## Part 3: The new table — workflow_runs

```
┌───────────────────────────────┐
│       workflow_runs           │
├───────────────────────────────┤
│ id              (int, PK)     │
│ lead_id         (int, FK)     │  ← points at leads.id
│ status          (str)         │  ← "running" / "completed" / "failed"
│ current_step    (str, null)   │  ← which station the car is at
│ started_at      (datetime)    │
│ finished_at     (datetime, null)
│ error_message   (str, null)   │  ← only set on failure
└───────────────────────────────┘
```

### Foreign keys, explained like you're 12

A foreign key is a "must point at something real" rule.

`lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)` means: this number must match the `id` of an actual row in the `leads` table. You cannot create a workflow run for lead #999 if lead #999 doesn't exist. The database itself refuses.

Analogy: a library checkout card must reference a real book on the shelf. You can't check out a book that doesn't exist. The FK is the librarian enforcing that.

Note the string is `"leads.id"` — the SQL table name, not the Python class name `Lead`.

### Why status lives on BOTH tables

- `Lead.status` = the lead's lifecycle ("new", "hot", "warm")
- `WorkflowRun.status` = one execution attempt's outcome ("running", "completed", "failed")

Different lifecycles, different columns. A lead could have three failed runs and one completed run; the lead's own status is a separate question.

### Nullable columns fill in over time

- `current_step` — set as the run progresses
- `finished_at` — set when the run ends
- `error_message` — set only if something failed

A fresh run has nulls in all three. That's not missing data; it's data that hasn't happened yet.

### Python defaults vs SQL defaults

`default="running"` in SQLAlchemy is a **Python-side** default: SQLAlchemy fills it in before the INSERT is sent. That's why `.schema` in sqlite3 shows no DEFAULT clause. (`server_default` would push it into the SQL — you rarely need that.)

---

## Part 4: orchestrator.py walkthrough

The full file, then the pieces:

```python
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import Lead, WorkflowRun


def log_lead(lead: Lead, db: Session) -> None:
    print(f"[log_lead] Lead {lead.id}: {lead.name} from {lead.company}")


def tag_priority(lead: Lead, db: Session) -> None:
    if "ceo" in lead.name.lower() or "founder" in lead.name.lower():
        lead.status = "hot"
    else:
        lead.status = "warm"
    db.commit()


WORKFLOW_STEPS = [
    ("log_lead", log_lead),
    ("tag_priority", tag_priority),
]


def run_workflow(lead: Lead, db: Session) -> WorkflowRun:
    run = WorkflowRun(lead_id=lead.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        for step_name, step_function in WORKFLOW_STEPS:
            run.current_step = step_name
            db.commit()
            step_function(lead, db)

        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)

    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)

    return run
```

### The steps

`log_lead` prints a line to the server log. Its job is proof-of-life: when you POST a lead, this line appearing in the uvicorn Terminal proves the workflow actually ran.

`tag_priority` mutates the lead: names containing "ceo" or "founder" get `status = "hot"`, everyone else gets `"warm"`. Assigning to a SQLAlchemy object's attribute marks it dirty; `db.commit()` writes it to disk.

### The steps list

```python
WORKFLOW_STEPS = [
    ("log_lead", log_lead),
    ("tag_priority", tag_priority),
]
```

A list of `(name_string, function)` tuples. The string gets recorded in the database (`current_step`); the function gets called. Adding a step = write the function, append a tuple. The orchestrator never changes.

Note there are no parentheses after the function names in the list. `log_lead` is the function itself (a thing you can pass around); `log_lead()` would CALL it immediately. We're storing the functions to call later. Functions in Python are values, like closures in Swift.

### The engine

```python
run = WorkflowRun(lead_id=lead.id, status="running")
db.add(run)
db.commit()
db.refresh(run)
```

Open the clipboard entry: a new run, status "running", persisted immediately. If you queried the table mid-run, you'd see it.

```python
for step_name, step_function in WORKFLOW_STEPS:
    run.current_step = step_name
    db.commit()
    step_function(lead, db)
```

The loop. For each station: record where we are, then do the work. `for a, b in list_of_tuples` unpacks each tuple into two variables — a clean Python idiom.

The commit BEFORE the step matters: if the step crashes, the database already knows which step was running. That's how `current_step` in a failed run tells you exactly where it broke.

```python
except Exception as exc:
    run.status = "failed"
    run.error_message = str(exc)
```

If any step raises, we land here. `Exception` is the base class of nearly all Python errors, so this catches everything. `str(exc)` turns the exception into a readable message for the database.

The server never crashes. The POST still returns 201. Only the run is marked failed. Graceful degradation.

---

## Part 5: New Python concepts in Phase 3

### f-strings

```python
print(f"[log_lead] Lead {lead.id}: {lead.name} from {lead.company}")
```

An `f"..."` string embeds expressions in curly braces. Swift equivalent: `"\(lead.id)"` interpolation.

### The `in` operator

```python
if "ceo" in lead.name.lower():
```

Substring check for strings. Also works on lists (`5 in [1,2,3]`) and dict keys. Very general.

### try / except (vs try / finally)

Phase 2 used `try/finally` (cleanup always runs). Phase 3 uses `try/except` (handle the error and keep going). You can combine all three: `try/except/finally`.

```python
try:
    risky()
except Exception as exc:
    handle(exc)   # runs only on failure
```

### Functions as values

```python
WORKFLOW_STEPS = [("log_lead", log_lead)]
step_function(lead, db)
```

Store a function in a list, pull it out, call it later. No parentheses = the function itself; parentheses = call it now.

### Tuple unpacking in loops

```python
for step_name, step_function in WORKFLOW_STEPS:
```

Each item is a 2-tuple; the loop unpacks it into two variables per iteration.

### Union types in Pydantic

```python
current_step: str | None
```

"A string OR null." Matches nullable database columns. Fields that always exist don't get `| None`.

---

## Part 6: The failure test (why we sabotaged our own code)

We temporarily added `raise ValueError("simulated failure for testing")` as the first line of `tag_priority`, POSTed leads, and confirmed:

- The runs showed `status: "failed"`
- `current_step: "tag_priority"` — exactly where it broke
- `error_message: "simulated failure for testing"` — captured
- The server stayed up; POSTs still returned 201

Then we removed the sabotage and confirmed a new run completed.

Why this matters: **untested error handling is decoration, not engineering.** The except branch had never executed until we forced it. Deliberately breaking your own code to watch the failure path run is a standard professional practice (the grown-up version is called fault injection / chaos testing).

Interview line this earns you: "I tested the failure path by injecting a fault and verifying the run was marked failed with the error captured, while the API stayed available."

---

## Part 7: Where this goes next

Phase 4 (Slack), Phase 5 (Anthropic email drafting), Phase 6 (Sheets) are all now the same move:

1. Write a function matching the step contract
2. Append `("name", function)` to `WORKFLOW_STEPS`

The orchestrator is done. That's the payoff of the design.

Known limitations (good interview answers when asked "what would you improve?"):
- Workflow runs synchronously inside the POST request — a slow step delays the API response. Fix: background tasks (FastAPI BackgroundTasks or a queue).
- Steps are hardcoded — one workflow for all leads. Fix: a Workflow table (deliberate deferral; we chose shipping over speculative flexibility).
- `create_all` can't alter existing tables — schema changes require deleting the dev database. Fix: Alembic migrations.
- No retries — a transient failure (network blip) permanently fails the run. Fix: retry with backoff per step.

Knowing the limitations and the fixes, without having built them, is exactly what "senior judgment" sounds like.
