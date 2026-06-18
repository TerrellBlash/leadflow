# leadflow Study Guide: Phase 1 + Phase 2

A real walkthrough of what you built, how it works, and why each piece is there. Written to be read slowly, not skimmed.

If something doesn't make sense, mark it. Come back to it. Concepts in Python build on each other; skipping a confusing one creates a debt that comes due later.

---

## Part 1: The Big Picture

### What is leadflow?

A small backend service that accepts incoming "lead" data (name, email, company) from somewhere on the internet, stores it in a database, and lets you read it back. The kind of thing a small business would use to capture form submissions from their website.

By the end of Phase 2, this is real:
- A web server running on your laptop
- Two endpoints: one to add a lead, one to list all leads
- A database file holding every lead you've added
- Auto-generated interactive documentation

You wrote it from scratch in Python.

### The pizza shop analogy

Think of leadflow as a pizza shop's order system.

- **FastAPI** is the front counter where customers place orders.
- **Uvicorn** is the front door of the shop. It accepts customers coming in from the street.
- **Pydantic** is the cashier who checks the order is valid. "You want a pizza? Okay. With cheese? Okay. With anchovies on a Tuesday? Sure." They reject nonsense before it reaches the kitchen.
- **SQLAlchemy** is the cook who writes orders down in the order book.
- **SQLite** is the order book itself. A physical notebook the shop keeps.
- **Your code in main.py** is the manager who tells everyone what to do.

When a lead "arrives," uvicorn opens the door, FastAPI hands the order to your manager, Pydantic checks it, SQLAlchemy writes it in the book, and the manager sends back a receipt with the order number on it. All in a few milliseconds.

---

## Part 2: Phase 1 in detail

### What you built in Phase 1

A web server with two endpoints:
- `GET /` returns `{"message": "leadflow is running."}`
- `GET /health` returns `{"status": "ok"}`

That's it. The point was to prove you could write Python that ran as a web server. Tiny, but real.

### The Python file (main.py at end of Phase 1)

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "leadflow is running."}


@app.get("/health")
def health():
    return {"status": "ok"}
```

Twelve lines. Let me explain each one as if you've never seen Python before.

#### Line 1: `from fastapi import FastAPI`

You're saying: "From the library called fastapi, give me one specific thing called FastAPI."

The library has many tools inside it. We only need one to start. Like going into a toolbox and pulling out just the wrench instead of carrying the whole box around.

The lowercase `fastapi` is the library's name. The uppercase `FastAPI` is a specific tool inside it (a "class"). Python cares about uppercase and lowercase being different.

**Swift comparison:** `import FastAPI` in Swift imports the whole module. Python's `from X import Y` is more specific: grab only Y from X.

#### Line 3: `app = FastAPI()`

You're saying: "Make a new FastAPI thing and call it 'app'."

The parentheses `()` mean "actually create one, please." It's like saying "give me a Coke" vs. just saying the word "Coke." The parentheses are the part that says "do it, not just name it."

You picked the name `app`. Could have been anything (`server`, `myApp`, `pizza`). But everyone in the FastAPI world uses `app`, so when we later run a command like `uvicorn main:app`, it works because we agreed to call it `app`.

#### Line 6: `@app.get("/")`

This is a **decorator**. The `@` symbol on a line is Python saying "I'm about to do something special to the function below."

What it does: "Take the function below this line. Tell `app` that whenever someone visits the URL `/`, run this function."

The `/` is a URL path. If your website is `example.com`, then `/` is `example.com/`, the homepage. `/health` would be `example.com/health`.

**Pizza shop analogy:** A decorator is like sticking a Post-it note on a cook's apron that says "you're in charge of the pizza orders." The cook is still the cook, but now they have a specific job.

#### Line 7: `def root():`

`def` means "define a function." This is Python's word for "I'm about to teach you a new thing to do."

`root` is the name we gave the function. We picked it because this function handles the root URL (`/`). It could be named anything.

`()` means "this function takes no arguments." If we wanted to pass it some data, we'd put it in the parentheses.

The `:` at the end opens a code block. Everything indented under it is the function's body.

**Swift comparison:** `func root() -> [String: String] { ... }`. The `def` is Python's `func`. The indented lines are the body, where Swift uses curly braces.

#### Line 8: `return {"message": "leadflow is running."}`

`return` means "the function's answer is this."

The curly braces with key-value pairs make a Python **dictionary**. It's a collection of labeled values. Here, the label is `"message"` and the value is `"leadflow is running."`.

When this gets sent over the internet, FastAPI converts the dictionary into **JSON**, which is the universal language for sending data between computers. Looks identical: `{"message": "leadflow is running."}`.

**Swift comparison:** `return ["message": "leadflow is running."]`. Python dictionaries and Swift dictionaries are basically the same idea, different syntax.

### Two ways to run the server

```bash
uvicorn main:app --reload
```

Versus the safer form:

```bash
python -m uvicorn main:app --reload
```

The first one *can* work, but if your Mac has multiple Python installations (you do), it might find the wrong uvicorn. The second one runs uvicorn as a module of *whatever Python is currently active*, which is what you want.

**Pizza shop analogy:** If you tell someone "go grab a pizza," they might come back with whatever pizza they find. If you tell them "go to MY kitchen and grab a pizza from THERE," you're being specific about which kitchen. `python -m` is being specific about which kitchen.

### The FastAPI free gift: `/docs`

Visit `http://localhost:8000/docs` and FastAPI builds you an interactive documentation page automatically. You wrote no documentation. FastAPI inspected your code and built it from the function names and decorators.

Every endpoint you add will show up there. This is one of FastAPI's selling points and a real productivity win.

---

## Part 3: Phase 2 in detail

### What you built in Phase 2

You took the toy server from Phase 1 and turned it into a real webhook system. Now:
- A `POST /leads` endpoint accepts new lead data
- Pydantic validates the incoming data (rejects bad emails, missing fields)
- SQLAlchemy writes the lead to a SQLite database file
- A `GET /leads` endpoint reads all leads back

The "internet" can now send data into your service and the service remembers it.

### The four-file architecture

Phase 2 stopped cramming everything into one file. You split it across four:

```
main.py        ← wires everything together, defines endpoints
database.py    ← how to connect to the database
models.py      ← the shape of a "lead" in the database
schemas.py     ← the shape of a "lead" in the API
```

**Pizza shop analogy:** A small shop had everything in one room: counter, kitchen, order book, storage. As the shop grows, you split it. Counter goes up front (main.py). Recipe book is in the kitchen (models.py). The customer-facing menu is on the wall (schemas.py). The plumbing for the cash register stays under the counter (database.py).

The split makes the shop easier to grow without tripping over yourself.

### Why "two models"? (THE most important concept in Phase 2)

The same idea ("a lead") shows up twice in your code:
- `Lead` in `models.py` (a SQLAlchemy class) describes a lead **in the database**
- `LeadIn` and `LeadOut` in `schemas.py` (Pydantic classes) describe a lead **in the API**

They're not the same lead. They're two views of the same concept.

**Restaurant analogy:** The kitchen has a recipe (lots of detail: ingredients, oven temperature, prep time). The menu has a description (fewer fields: name, price). The customer sees the menu version. The kitchen uses the recipe version. Same dish, two representations, different audiences.

In your code:
- The **kitchen recipe** is `Lead` in `models.py`. All six columns: `id`, `name`, `email`, `company`, `status`, `created_at`.
- The **customer menu** for incoming orders is `LeadIn` in `schemas.py`. Only three fields: `name`, `email`, `company`. The customer doesn't get to set `id` or `status`.
- The **customer menu** for outgoing receipts is `LeadOut` in `schemas.py`. All six fields shown. The customer sees the full receipt with their order number.

This split is what protects you. If you let the customer set the order number directly, they could pretend to be order #5 when they're actually order #99. The two-model split makes that impossible.

### The lead table

```
┌─────────────────────────────────────────────┐
│  TABLE: leads                                │
├──────────────┬──────────────┬───────────────┤
│  column      │  type        │  who sets it  │
├──────────────┼──────────────┼───────────────┤
│  id          │  integer     │  database     │
│  name        │  text        │  sender       │
│  email       │  text        │  sender       │
│  company     │  text        │  sender       │
│  status      │  text        │  system       │
│  created_at  │  datetime    │  system       │
└──────────────┴──────────────┴───────────────┘
```

The "who sets it" column matters. Three sources of data, three different trust levels.

### database.py walkthrough

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./leadflow.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
```

Three things this file produces, used everywhere else:

1. **`engine`**: the physical connection to the database file. The pipe from your code to the SQLite file on disk. Created once, reused forever.

2. **`SessionLocal`**: a factory. You call `SessionLocal()` and get back a fresh "conversation" with the database. Each web request gets its own conversation, used briefly, then closed.

3. **`Base`**: a parent class. Every table you define in `models.py` inherits from `Base`. The inheritance is how SQLAlchemy tracks what tables exist.

**Pizza shop analogy:**
- `engine` is the wire connecting the shop's order tablet to the cloud database. Plugged in once, stays plugged in.
- `SessionLocal` is the stack of order forms by the register. Cashier grabs a fresh one for each customer, fills it in, files it.
- `Base` is the official template every form in the shop is based on. Order forms, supply forms, complaint forms, all inherit from the official template.

#### The weird SQLite-only line

```python
connect_args={"check_same_thread": False}
```

SQLite is paranoid about being used from more than one thread. FastAPI uses multiple threads. So we tell SQLite "relax, it's fine." This line is SQLite-specific. If you switch to Postgres later, you remove it.

### models.py walkthrough

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

`class Lead(Base):` says "Lead is a kind of Base." Because Base was made by SQLAlchemy's `declarative_base()`, inheriting from it registers Lead as a database table.

`__tablename__ = "leads"` is the actual table name in the database. The Python class is `Lead` (singular, capital). The SQL table is `leads` (lowercase plural). Standard convention.

Each `column_name = Column(Type, ...options)` line defines one column. Three options to know:

- **`primary_key=True`**: this column uniquely identifies a row. Used on `id`.
- **`nullable=False`**: this column cannot be empty. A lead with no name is rejected.
- **`default=value`** or **`default=function`**: if no value is provided, use this.

#### The lambda trap (genuinely important)

Look at this line:

```python
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

The `lambda:` is critical. Without it, this would break in a subtle way.

`lambda:` means "this is a tiny function that returns the value when called." Without it, you'd write:

```python
default=datetime.now(timezone.utc)  # WRONG
```

That looks fine but breaks. Why? Because `datetime.now()` runs **immediately, when the file loads**, and freezes that one moment in time. Every lead created after that gets the same timestamp. Forever.

With `lambda:`, the function runs **each time a new lead is inserted**, so each lead gets its own correct timestamp.

**Analogy:** If you say "the time NOW is 3 PM" and put that note on the wall, the note will say 3 PM forever, even at midnight. If you instead put a working clock on the wall, it always shows the right time. `lambda:` is the working clock.

This is a real classic Python bug called "early evaluation of mutable defaults." Worth filing away.

### schemas.py walkthrough

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

Two Pydantic models. Both inherit from `BaseModel`, the same way SQLAlchemy classes inherit from `Base`.

`LeadIn` has three fields. Each line says "this field must be of this type." `name: str` means name must be a string. `email: EmailStr` means it must be a properly-formatted email.

The type annotations are the validation. There's no separate `validate_email()` call. The type `EmailStr` is itself the rule.

When a request comes in, Pydantic reads the JSON body and tries to make a `LeadIn` from it. If the JSON has `email: "not-real"`, Pydantic returns a 422 error before your function ever runs. Your function only sees valid data.

#### The from_attributes=True line

```python
model_config = ConfigDict(from_attributes=True)
```

This appears only on `LeadOut`. Here's why.

By default, Pydantic only knows how to read from dictionaries: `{"name": "Sarah", ...}`. But when we return a lead from the API, we'll have a SQLAlchemy `Lead` *object* in hand, not a dictionary. The object has attributes (`lead.name`) but not dictionary keys.

`from_attributes=True` tells Pydantic: "if I give you a Python object, read its attributes instead of treating it like a dictionary."

This is the bridge that lets SQLAlchemy objects flow into Pydantic responses.

### main.py walkthrough (the new parts)

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

#### `Base.metadata.create_all(bind=engine)`

This line, run once at startup, creates the `leads` table in SQLite if it doesn't exist.

`Base.metadata` is SQLAlchemy's catalog of every table you defined (one in this project: Lead). `create_all` says "build all tables in this catalog." `bind=engine` says "build them in the database that this engine connects to."

First time the server starts, this creates `leadflow.db` and the `leads` table inside it. Subsequent starts, the file and table already exist, so it does nothing.

#### `get_db()`: lifecycle management

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Five lines doing one job: open a database session, give it to whoever needs it, close it afterward no matter what.

`yield` is not `return`. A function with `yield` is a generator. It hands a value back, pauses, and resumes later.

`try: ... finally:` is Python's "do this, and run the finally part no matter what." Same idea as Swift's `defer`.

Combined: "open session, hand it out, when whoever's using it is done (success or crash), close the session."

**Pizza shop analogy:** A cashier opens a register at the start of a transaction, lets the customer pay, then closes the register. They close it even if the credit card was declined. They close it even if the building catches fire. Every transaction, the register gets closed. That's `get_db`.

#### The POST endpoint

```python
@app.post("/leads", response_model=LeadOut, status_code=201)
def create_lead(payload: LeadIn, db: Session = Depends(get_db)):
```

The decorator says:
- It's a POST endpoint at `/leads`
- The response body should match `LeadOut` (six fields)
- Success returns HTTP status code 201 (Created), not the default 200 (OK)

The function parameters say:
- `payload: LeadIn` means "read the request body and validate it as a LeadIn". FastAPI sees the Pydantic type and does this automatically.
- `db: Session = Depends(get_db)` means "call get_db() and pass me what it yields, as `db`". FastAPI sees the Depends marker and does this automatically.

Two parameters, two completely different sources. FastAPI figures out which source by looking at the type hints. This is FastAPI's "magic", really just clever use of Python's type annotations.

Inside the function:

```python
lead = Lead(name=payload.name, email=payload.email, company=payload.company)
db.add(lead)
db.commit()
db.refresh(lead)
return lead
```

Step by step:
1. Build a new `Lead` from the validated payload
2. `db.add(lead)` stages it ("I want to save this")
3. `db.commit()` actually writes it to disk
4. `db.refresh(lead)` reads back the auto-generated fields (id, created_at) into our object
5. Return the lead. FastAPI converts it to `LeadOut` for the response.

### The full request flow

```
Browser/curl sends JSON
        ↓
uvicorn accepts the HTTP request
        ↓
FastAPI reads the body
        ↓
Pydantic validates against LeadIn
   (rejects with 422 if invalid)
        ↓
get_db() opens a session
        ↓
create_lead builds a Lead object
        ↓
db.add → db.commit → db.refresh
   (lead is now persisted)
        ↓
Function returns the Lead
        ↓
FastAPI converts Lead → LeadOut
        ↓
JSON response, status 201
        ↓
get_db()'s finally block closes the session
```

---

## Part 4: The Python concepts you used

A consolidated list of Python ideas from Phase 1 and Phase 2.

### Imports

```python
import x
from x import y
from x.y import z
```

These find a module and pull names from it. The names go into your file's local namespace so you can use them directly.

### Variables

```python
app = FastAPI()
```

No `let` or `var` needed. The variable exists once you assign to it.

### Functions

```python
def name(arg1, arg2):
    do_something
    return result
```

The colon opens a block. Indentation (4 spaces) defines the block's contents. Python uses indentation where Swift uses curly braces.

### Type hints

```python
def create_lead(payload: LeadIn, db: Session):
```

The `: LeadIn` after `payload` is a **type hint**. Python doesn't enforce it at runtime, but tools (Pydantic, FastAPI) read it to decide how to process the parameter.

In FastAPI, type hints are not optional decoration; they drive the framework's behavior.

### Classes and inheritance

```python
class LeadIn(BaseModel):
    name: str
```

`class Name(Parent):` defines a class that inherits from another. The body has indented attributes and methods.

### Decorators

```python
@app.get("/leads")
def list_leads():
    ...
```

The `@` line wraps the function below it. The decorator can add behavior, register the function somewhere, or transform it.

### Dictionaries

```python
{"key": "value", "another": 42}
```

Key-value pairs. JSON-compatible. Returned from endpoints, accepted as arguments.

### Generators and yield

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

A function with `yield` is a generator. It produces a value, pauses, and resumes when the caller is done. Useful for managed-resource patterns.

### try / finally

```python
try:
    risky_thing()
finally:
    cleanup()
```

`finally:` runs no matter what. Success or crash, cleanup happens.

### Lambdas

```python
default=lambda: datetime.now(timezone.utc)
```

A lambda is a small anonymous function. `lambda: X` is "a function that returns X." Used here to defer evaluation: compute X each time the lambda is called, not once when the file loads.

---

## Part 5: The war stories (the real lessons)

Things that broke in your real session. These are more educational than any tutorial.

### War story 1: pip broke after a wrong-environment install

**What happened:** You ran `pip install` from a Terminal where the venv wasn't active, so packages went into Anaconda's global Python. Then you ran `pip install --upgrade pip` from within the venv, which removed pip's actual code while leaving the launcher script. Pip "existed" but couldn't run.

**Lesson:** Always confirm your prompt shows `(venv_name)` before running `pip`. Use `python -m pip` instead of bare `pip` to anchor pip to the active Python.

### War story 2: half-built venv missing the lib/ directory

**What happened:** A venv rebuild got interrupted (probably by Terminal switching). The `.venv/bin/` had launchers, but `.venv/lib/` didn't exist. Every pip command failed in confusing ways.

**Lesson:** Virtual environments are disposable. When in doubt, `rm -rf .venv` and rebuild. Your code is never inside the venv; only installed libraries are.

### War story 3: switched to uv because of Anaconda interference

**What happened:** Your Mac has Anaconda plus four Python framework installs. The plain `venv` tool couldn't navigate the chaos. Pip kept dying.

**Lesson:** uv is a modern alternative to venv + pip. It manages its own Python interpreters and creates environments atomically. For machines with conflicting Python installs, it's a better tool. The fix command: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

### War story 4: bare uvicorn used wrong Python

**What happened:** Even after fixing the venv, `uvicorn main:app --reload` was finding a uvicorn from system Python 3.13 (which lacked your packages) instead of the venv's Python 3.11.

**Lesson:** `python -m uvicorn main:app --reload` instead of `uvicorn main:app --reload`. The `python -m` prefix forces the active Python to be the one running uvicorn. Adopt this habit permanently.

### War story 5: --reload watched the venv and caused asyncio crashes

**What happened:** uvicorn's default `--reload` watches every file in the current directory tree, including `.venv/` (thousands of library files). On startup, an in-flight request was crashed mid-execution by a spurious reload triggered by venv file timestamps. The crash showed up as `KeyError: 'asyncio'` deep in anyio.

**Lesson:** Use `--reload-exclude '.venv/*'` to keep the venv out of the watch list. Real symptoms can manifest deep in stack traces of unrelated libraries; the root cause is often something simple like file watching.

### War story 6: a stray `3` after `try:` broke the file

**What happened:** Accidentally typed `try:3` instead of `try:`. Python's syntax error appeared on the wrong line (where `yield db` was) because Python parses left-to-right and only realized something was wrong further down.

**Lesson:** Python syntax errors often point at the line *after* the actual mistake. When you see one, look at the error line AND a few lines above. Modern editors catch these with red squiggles.

---

## Part 6: How to come back to this project tomorrow

Three steps every time:

1. **Open Terminal:**
   ```bash
   cd ~/Desktop/leadflow
   source .venv/bin/activate
   ```
   Confirm your prompt shows `(leadflow) ... leadflow %`.

2. **Start the server:**
   ```bash
   python -m uvicorn main:app --reload --reload-exclude '.venv/*'
   ```
   Or, if you set up `run.sh`, just `./run.sh`.

3. **Open Cursor on the folder:**
   ```bash
   cursor .
   ```
   In a second Terminal tab so the first one keeps showing uvicorn logs.

Visit `http://localhost:8000/docs` to see your endpoints.

---

## Part 7: Where you are vs. where you're going

**What's done:** A backend service that accepts and stores leads. Solid foundation.

**Phase 3 next:** The orchestrator. Take an incoming lead and run a sequence of steps on it (log it, score it, prepare a notification). This is what turns a webhook into a workflow system.

**Phase 4-7 after that:** Slack notifications, Gmail email drafting with Anthropic Claude, Google Sheets logging, Docker, deployment to Render, README, demo video, LinkedIn post.

Phase 2 was the hardest because it's the most concept-dense. Phase 3 will feel easier because the foundation is solid.

---

## Notes to self

Whenever you sit back down with this project, remind yourself:

- The four files have specific jobs. Don't cram things into the wrong file.
- The `LeadIn` vs `LeadOut` split is the architectural decision. Respect it.
- Python tracebacks read bottom-up.
- When pip or uvicorn does something weird, ask: "is my venv active?" 90% of the time, that's the answer.
- This project is real. It works. You wrote it.
