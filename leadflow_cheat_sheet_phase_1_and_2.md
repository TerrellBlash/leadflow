# leadflow Cheat Sheet: Phase 1 + Phase 2

Quick reference. For when you forgot the command. Read the study guide for explanations; come here for the answer.

---

## Terminal Setup (every new session)

```bash
cd ~/Desktop/leadflow
source .venv/bin/activate
```

Confirm prompt shows `(leadflow) ... leadflow %` before running anything.

---

## Server Commands

| What you want | Command |
|---|---|
| Start dev server | `python -m uvicorn main:app --reload --reload-exclude '.venv/*'` |
| Stop server | `Ctrl + C` in the running Terminal |
| Visit the docs | http://localhost:8000/docs |
| Visit the redoc page | http://localhost:8000/redoc |
| Test root | http://localhost:8000/ |
| Test health | http://localhost:8000/health |
| Test list leads | http://localhost:8000/leads |

Always use `python -m uvicorn`, not bare `uvicorn`. The `python -m` prefix forces the venv's Python.

---

## Package Management (uv, not pip)

| What you want | Command |
|---|---|
| Install a package | `uv pip install <name>` |
| Install with extras | `uv pip install "<name>[extra]"` |
| Install everything from a lockfile | `uv pip install -r requirements.txt` |
| List installed packages | `uv pip list` |
| Lock current environment to file | `uv pip freeze > requirements.txt` |
| Rebuild venv from scratch | `rm -rf .venv && uv venv --python 3.11 && source .venv/bin/activate` |

Quotes around `[extra]` are needed because shells interpret square brackets.

---

## Git

| What you want | Command |
|---|---|
| Initialize repo | `git init` |
| See what's changed | `git status` |
| Stage everything | `git add .` |
| Stage one file | `git add main.py` |
| Commit staged changes | `git commit -m "your message"` |
| See commit history | `git log --oneline` |
| Push to GitHub (after adding remote) | `git push -u origin master` |
| Add a remote | `git remote add origin <url>` |

---

## File Structure

```
leadflow/
├── .gitignore           # what NOT to track (.venv/, *.db, etc.)
├── requirements.txt     # pinned dependencies
├── main.py              # FastAPI app + endpoints
├── database.py          # SQLite connection setup
├── models.py            # SQLAlchemy table (Lead)
├── schemas.py           # Pydantic shapes (LeadIn, LeadOut)
├── leadflow.db          # SQLite database file (auto-created, gitignored)
└── .venv/               # virtual env (gitignored)
```

---

## The Four Files at a Glance

### main.py: ties everything together

```python
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine
from models import Lead
from schemas import LeadIn, LeadOut

Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/leads", response_model=LeadOut, status_code=201)
def create_lead(payload: LeadIn, db: Session = Depends(get_db)):
    lead = Lead(name=payload.name, email=payload.email, company=payload.company)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@app.get("/leads", response_model=list[LeadOut])
def list_leads(db: Session = Depends(get_db)):
    return db.query(Lead).all()
```

### database.py: connection setup

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./leadflow.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite + FastAPI only
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
```

### models.py: the leads table

```python
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime

from database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    company = Column(String, nullable=False)
    status = Column(String, default="new")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

### schemas.py: API shapes

```python
from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class LeadIn(BaseModel):
    name: str
    email: EmailStr
    company: str


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    company: str
    status: str
    created_at: datetime
```

---

## Adding a New Endpoint (template)

Inside `main.py`:

```python
@app.METHOD("/path", response_model=ResponseShape, status_code=CODE)
def function_name(param: RequestShape, db: Session = Depends(get_db)):
    # do work here
    return result
```

Where:
- `METHOD` is `get`, `post`, `put`, `delete`, `patch`
- `response_model` is a Pydantic class (or `list[Class]`, or omit)
- `status_code` defaults to 200; common alternatives: 201 (Created), 204 (No Content)
- `param: RequestShape` reads the request body and validates it
- `Depends(get_db)` injects a database session

---

## Adding a New Column to the leads Table

1. Add the column in `models.py`:
   ```python
   phone = Column(String, nullable=True)
   ```
2. Add the field to `LeadIn` and/or `LeadOut` in `schemas.py`:
   ```python
   phone: str | None = None
   ```
3. **Delete leadflow.db** to force recreation with the new schema. (`Base.metadata.create_all` doesn't migrate existing tables; for that you need Alembic.)
4. Restart uvicorn.

---

## HTTP Status Codes You'll See

| Code | Meaning | When |
|---|---|---|
| 200 | OK | Successful GET |
| 201 | Created | Successful POST that created something |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Malformed request |
| 404 | Not Found | URL doesn't exist |
| 422 | Unprocessable Entity | Pydantic validation failed (bad email, missing field) |
| 500 | Internal Server Error | Your code crashed; check the uvicorn Terminal |

---

## Common Errors and Fixes

| Error message | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'X'` | venv not active, OR package not installed | `source .venv/bin/activate`, then `uv pip install X` |
| `No module named pip` | pip broken in venv | `rm -rf .venv && uv venv --python 3.11 && source .venv/bin/activate && uv pip install -r requirements.txt` |
| `KeyError: 'asyncio'` in anyio | uvicorn reload watching venv | Use `--reload-exclude '.venv/*'` |
| `SyntaxError: expected 'except' or 'finally' block` | Stray text on a `try:` line, or missing block | Check the line in the error AND a few lines above |
| `500 Internal Server Error` (no detail) | Code crashed | Read the traceback in the uvicorn Terminal |
| `422 Unprocessable Entity` | Pydantic rejected the request | Response body shows which field failed |
| Wrong Python version in tracebacks | Bare `uvicorn` resolved to system Python | Use `python -m uvicorn` instead |

---

## Python Syntax Quick Reference

### Function

```python
def name(arg: Type) -> ReturnType:
    return value
```

### Class

```python
class Name(ParentClass):
    attribute: Type

    def method(self, arg):
        return value
```

### Import

```python
import module                  # all of module, called as module.thing
from module import thing        # just thing, called as thing
from module import a, b, c      # multiple things
from package.submodule import x # nested
```

### Dictionary

```python
{"key": "value", "another": 42}
```

### List

```python
[1, 2, 3]
```

### Decorator

```python
@decorator_name
def function():
    pass
```

### Try/Finally

```python
try:
    risky()
finally:
    cleanup_always_runs()
```

### Generator

```python
def gen():
    yield value  # pauses here, resumes when caller is done
```

### Lambda

```python
default_func = lambda: compute_each_time()
```

---

## Pydantic Type Hints Quick Reference

| Type | Validates |
|---|---|
| `str` | Any string |
| `int` | Whole number |
| `float` | Decimal number |
| `bool` | True or False |
| `datetime` | ISO format date/time |
| `EmailStr` | Properly formatted email (needs `pydantic[email]` installed) |
| `list[X]` | List where every item is X |
| `dict[str, X]` | Dictionary with string keys, X values |
| `X \| None` | X or null (optional field) |

---

## SQLAlchemy Column Types Quick Reference

| Column type | Stores |
|---|---|
| `Integer` | Whole numbers |
| `String` | Text |
| `Text` | Long text |
| `Boolean` | True/False |
| `DateTime` | Date and time |
| `Float` | Decimal numbers |

### Column options

| Option | Effect |
|---|---|
| `primary_key=True` | This is the unique row identifier |
| `nullable=False` | Cannot be empty |
| `default=value` | Use this if not provided (use a `lambda:` if you want it re-evaluated each row) |
| `index=True` | Create a database index for fast lookups |
| `unique=True` | Reject duplicate values |

---

## SQLAlchemy Session Operations

| Action | Code |
|---|---|
| Open session | `db = SessionLocal()` |
| Add new row | `db.add(obj)` |
| Save to disk | `db.commit()` |
| Reload from disk (gets auto-assigned id, timestamps) | `db.refresh(obj)` |
| Close session | `db.close()` |
| Query all rows | `db.query(Lead).all()` |
| Query with filter | `db.query(Lead).filter(Lead.status == "new").all()` |
| Get one row | `db.query(Lead).filter(Lead.id == 1).first()` |
| Delete a row | `db.delete(obj); db.commit()` |

---

## Testing the API

### Using the docs page (easiest)

1. Visit http://localhost:8000/docs
2. Click an endpoint to expand
3. Click `Try it out`
4. Fill in the request body (for POST/PUT)
5. Click `Execute`
6. Look at the response below

### Using curl from Terminal

```bash
# GET
curl http://localhost:8000/leads

# POST
curl -X POST 'http://localhost:8000/leads' \
  -H 'Content-Type: application/json' \
  -d '{"name": "Test", "email": "test@example.com", "company": "TestCo"}'
```

---

## Reading a Python Traceback

1. Find `Traceback (most recent call last):`
2. Scroll to the **bottom** of the trace
3. The very last line tells you the error type and message
4. The line above it tells you which file and line number
5. The cause is usually at the bottom; the framework code at the top is just the path that got there

```
File "/your/file.py", line 16, in get_db
    yield db
                            ← the error message below
SyntaxError: expected 'except' or 'finally' block
```

---

## Habits Worth Building

| Bad habit | Good habit | Why |
|---|---|---|
| `pip install` | `python -m pip install` (or `uv pip install`) | Anchors to active env |
| `uvicorn main:app` | `python -m uvicorn main:app` | Same; avoids using wrong Python |
| `pip install --upgrade pip` | Don't, unless you really need to | The cause of one of your venv breakages |
| `git add -A` | `git add specific_file.py` | Don't accidentally commit secrets |
| Skipping `git status` before committing | Always check first | Prevents committing the wrong files |
| Cramming everything into main.py | Split into models.py, schemas.py, services.py, etc. | Easier to grow; easier to read |
| Skipping the venv activation | Activate before any pip/python command | Avoids 90% of "weird" Python errors |

---

## Project URLs (when server is running)

| URL | What |
|---|---|
| http://localhost:8000/ | Root (if you have a `@app.get("/")` route) |
| http://localhost:8000/health | Health check |
| http://localhost:8000/leads | GET: all leads. POST: create lead. |
| http://localhost:8000/docs | Interactive API docs (Swagger UI) |
| http://localhost:8000/redoc | Alternative docs (ReDoc) |
| http://localhost:8000/openapi.json | Machine-readable API spec |

---

## End of cheat sheet

Bookmark this. Open it when you're stuck. Don't try to memorize it; lookups are normal.
