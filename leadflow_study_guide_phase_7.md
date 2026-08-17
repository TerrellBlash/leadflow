# leadflow Study Guide: Phase 7 — Deployment

Addendum to the Phase 1-5 study guides. (Phase 6, Google Sheets, was deliberately skipped. Reasoning is in Part 1.)

---

## Part 1: Why Phase 6 got skipped

Phase 6 was Google Sheets logging: a third external integration. It was skipped in favor of going straight to deployment, for a reason worth understanding because it generalizes.

Slack demonstrates "can integrate a third-party API." Anthropic demonstrates it again. Sheets would demonstrate it a third time while costing a full session of Google Cloud console setup, service account credentials, and OAuth debugging. Meanwhile the project had no public URL, no README, and no way for anyone to see it work.

The handoff document that started this project was blunt: a hire-me project sitting on your laptop is worth nothing. Every session spent on a fourth integration is a session not spent making the first three visible to anyone.

**The generalizable principle: ship the thing, then extend it.** Because of the step contract from Phase 3, adding Sheets later is a function plus a tuple. Deployment is not something you can bolt on as easily once attention has moved on.

---

## Part 2: What breaks in production that doesn't break locally

Three assumptions your laptop lets you make that a deployment platform does not.

### The filesystem is not permanent

Render's containers get a fresh disk on every deploy, restart, or crash. `leadflow.db` would be wiped silently and repeatedly. Leads would vanish with no error message.

This is called an **ephemeral filesystem** and it is the norm for container platforms, not a Render quirk. The design assumption is that containers are disposable, so anything that must survive lives outside the container: a managed database, object storage, an external cache.

The fix was Postgres. The interesting part is how little it cost.

### The port is assigned, not chosen

Locally you pick 8000. Render sets a `PORT` environment variable and expects the app to listen on it. Hardcoding 8000 produces a container that builds, starts, appears healthy in the logs, and refuses every connection.

Handled in the Dockerfile: `--port $PORT`.

### Binding to localhost makes the app unreachable

Uvicorn defaults to `127.0.0.1`, meaning "accept connections from this machine only." Inside a container, "this machine" is the container itself. Traffic from outside never arrives.

`--host 0.0.0.0` means "accept connections on all network interfaces." This is one of the most common first-deploy failures, and the symptom is identical to the port problem: healthy logs, dead endpoint.

---

## Part 3: The database swap, and why it was one line

The change in `database.py`:

```python
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./leadflow.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
```

Three things worth understanding.

**`os.environ.get(key, default)`** takes a fallback as its second argument. Unset locally, you get SQLite. Set on Render, you get Postgres. One expression covers both environments and no other file in the project needs to know which one it is running against.

**The conditional expression** `X if condition else Y` is new syntax. It evaluates to `X` when the condition holds, otherwise `Y`. Here it exists because `check_same_thread` is a SQLite-only setting from Phase 2; passing it to Postgres would raise an error. Same idea as an if/else block, collapsed to a single value.

**Nothing else changed.** Not `models.py`, not `schemas.py`, not `orchestrator.py`, not a single query. That is what an ORM buys: SQLAlchemy speaks a common dialect and translates it per backend. `psycopg2-binary` was installed as the driver, and SQLAlchemy picks it automatically based on the `postgresql://` prefix in the connection string.

The interview version: "I used SQLAlchemy rather than raw SQL. The cost is a layer of abstraction. The benefit showed up at deploy time, when moving from SQLite to Postgres was a config change instead of a rewrite."

---

## Part 4: Docker

### What a container is

A container is a box holding your app plus everything it needs: the Python version, the libraries, the OS pieces underneath. You hand the platform the box instead of your source code plus a hope that their machine resembles yours.

The mental model that makes it click: for five phases you have been telling a person the setup steps. Install Python 3.11. Make a venv. Install requirements. Run uvicorn. A Dockerfile is those same steps written for a machine.

### The Dockerfile, line by line

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
```

**`FROM python:3.11-slim`** starts from a prebuilt image with Python 3.11 on a minimal Linux. `slim` is stripped down: smaller image, faster deploys. Matching the local Python version is deliberate.

**`WORKDIR /app`** sets the working directory inside the container for everything that follows.

**`COPY requirements.txt .` then `RUN pip install`** copies only the requirements file, then installs. Copying the whole project first would work but would be slower on every rebuild, because of layer caching.

**Layer caching** is worth understanding properly. Each Dockerfile instruction produces a cached layer, and a layer is only rebuilt if its inputs changed. Copying requirements alone means the expensive install step is skipped whenever you change only Python files. Copy everything first and every code edit reinstalls all 34 packages. This ordering is the single most common Dockerfile optimization and it is a fair interview question.

**`COPY . .`** copies the rest of the project.

**`CMD uvicorn main:app --host 0.0.0.0 --port $PORT`** runs when the container starts. Three differences from the local command: `--host 0.0.0.0` for reachability, `--port $PORT` to accept the platform's assignment, and no `--reload`, which is a development convenience that wastes resources and can restart mid-request.

### .dockerignore

Same idea as `.gitignore`, different consumer.

```
.venv/
__pycache__/
*.pyc
.git/
.env
*.db
*.md
.DS_Store
.vscode/
```

**`.env` is on that list and it matters most.** Secrets never belong in a container image. Anyone who pulls the image can read its contents. The platform supplies environment variables separately at runtime, which is why `os.environ.get()` works identically in both places while the secret lives in exactly one.

**`.venv/` matters too.** Thousands of files, built for macOS, useless inside a Linux container. The container builds its own environment from `requirements.txt`.

---

## Part 5: The deploy itself

Order matters: database first, then web service, because the service needs the database's connection string.

### Postgres on Render

Created through the dashboard. Two things to watch:

**The free tier is not the default.** The database creation page presented a paid configuration and prompted for a card. The free option existed but had to be selected. Read the monthly total before clicking create.

**Use the Internal Database URL, not the External one.** Internal routes over Render's private network: faster, no egress cost, and only resolves between services in the same region. This is why the web service had to be created in the same region as the database.

### The web service

Render detected the Dockerfile and set the runtime automatically. The three environment variables (`DATABASE_URL`, `ANTHROPIC_API_KEY`, `SLACK_WEBHOOK_URL`) went into Render's secret storage, which is the production counterpart of `.env`. Same variable names, same `os.environ.get()` calls, different storage.

A typo in one of those names (`LACK_WEBHOOK_URL` instead of `SLACK_WEBHOOK_URL`) would have produced a runtime failure in `notify_slack` rather than a build failure, which is the more annoying kind: the deploy succeeds, and one step fails silently on every lead. Environment variable names are string matches against your code, with no compiler to catch a mismatch.

### Reading the build log

The successful deploy, in order:

```
#9  RUN pip install ...        installing 34 packages
#10 COPY . .                   your code into the image
#11 exporting to image         packaging the layers
#12 exporting cache            saving layers for next time
==> Deploying...
INFO: Uvicorn running on http://0.0.0.0:10000
==> Your service is live
```

`0.0.0.0:10000` is worth noticing: the host flag worked, and Render assigned port 10000 through `$PORT`. Neither number was in the code.

---

## Part 6: The README, and what hiring readers actually do

Research on how technical portfolios are reviewed produced a few things worth internalizing, because they are counterintuitive.

### The read is measured in seconds

Surveys of hiring professionals put the initial screening pass under a minute. One engineer who ran first-round technical screening described opening a repository, scanning the README, and deciding within roughly ten seconds whether to keep reading. The reader is pattern matching for "this person builds and ships," not auditing your architecture.

**Consequence for structure:** setup instructions do not go at the top. The order that matches reader priority is problem, then working demo, then architecture, then evidence, then setup, then decisions, then limitations. A tech stack list as the opening line answers a question nobody asked first.

### Specificity is the entire signal

"Built a task management app using React" and "deployed a task tracker used by 15 people, cutting manual tracking time by about 30 percent" describe the same work. Only one is credible.

The same applies at the sentence level. "Leverages cutting-edge AI to seamlessly revolutionize lead management" says nothing. "Runs an ordered pipeline of four steps, recording each step's state so a failed run reports which step it died on" says what it does.

### AI-generated writing is now a recognized tell, and it costs credibility

The patterns hiring readers report noticing: an emoji before every heading, em-dashes used as connective filler, a specific vocabulary cluster (delve, leverage, seamless, robust, comprehensive, pivotal, tapestry), the "not only X but also Y" cadence, and uniform sentence length throughout.

Any one of these is nothing. The cluster, combined with an absence of specifics, is what registers. Worth caring about for this project in particular: leadflow calls the Claude API, so a README that reads like unedited model output undercuts the work it describes.

### Admitting limitations helps

This was the clearest finding and the least intuitive. Every source that addressed it, from engineering hiring managers to technical recruiters, said a specific limitations section builds credibility rather than costing it. One engineering leadership piece flagged the opposite as the warning sign: be alarmed by a candidate who claims no weaknesses.

**The wording rule: name the boundary and its consequence, and do not apologize.**

Weak: "Unfortunately I didn't have time to add tests, sorry."

Strong: "Tests are manual. Endpoints were exercised through the OpenAPI docs and failure paths through deliberate fault injection. There is no pytest suite."

The one way it backfires is describing planned work as though it exists. Present tense for what is built; everything else under limitations.

### What is table stakes versus differentiating in AI work

"Integrated an LLM API" no longer distinguishes anyone. What hiring loops probe in 2026: how you evaluate output quality, how you handle hallucination, whether outputs are structurally validated, whether you track cost and latency, whether prompts are versioned, and for anything agentic, whether steps are idempotent and how retries behave.

leadflow has prompt versioning, per-step state tracking, and failure isolation. It does not have evals, cost tracking, retries, or idempotency.

**Both of those facts went into the README.** The first group in the body, the second group in Limitations. Writing evals into a README that has no evals is the fastest way to fail the interview that README earns you, because Limitations is the section an experienced reader probes first.

---

## Part 7: The war story, Phase 7 edition

### The free tier that wasn't

Creating the Postgres database landed on a paid configuration by default, complete with a Stripe card prompt showing a monthly total. The free option existed one section up the page.

Nothing was broken. It is worth recording because the failure mode is quiet: you enter a card, the deploy works, and you find the charge later. **On any platform's create-resource page, read the total before clicking create.** Free tiers are usually available and usually not the default.

### 404 as a first impression

The first live URL returned `{"detail":"Not Found"}`, because the root endpoint had been deleted back in Phase 2 and never replaced. Technically correct: no route at `/`, so FastAPI returns 404.

But the bare URL is what a recruiter clicks. A 404 reads as broken regardless of what the API does at other paths. Three lines fixed it.

**The lesson is about audience.** Every endpoint decision until this point was made for a developer reading `/docs`. The moment the URL became public, a different reader existed, one who will not try a second path.

---

## Part 8: Where the project stands

**Live and working:** a POST to a public URL validates a lead, persists it to managed Postgres, runs four ordered steps with recorded state, generates an AI draft, and posts to Slack. Deployed from a Dockerfile, redeployed automatically on every push to main.

**What Phase 7 taught, beyond the commands:** ephemeral filesystems and why persistence lives outside the container; environment-driven configuration as the thing that makes one codebase run in two places; layer caching and why Dockerfile line order matters; the difference between a build failure and a runtime failure caused by a mistyped environment variable name; and how a portfolio is actually read.

**The highest-value remaining work, in order:**

1. **A pytest suite.** The largest gap, and the easiest to close. A handful of tests against `/health`, a valid POST, an invalid POST returning 422, and the orchestrator's failure path would remove the largest item from Limitations.
2. **Move the workflow off the request path.** FastAPI's `BackgroundTasks` is the small version. This is the limitation that actually matters at any real volume.
3. **Prompt v2 plus a comparison.** The drafts table was built for this. Running it converts "I noticed the model hallucinates" into "I measured it and here is what changed."
4. **A `GET /drafts` endpoint.** The schema exists. Five lines.
5. **Alembic.** The correct answer to schema migrations, and the thing that makes the project's database story production-shaped rather than development-shaped.

Each of these moves an item out of Limitations and into the body of the README. That is a useful way to think about a portfolio project's roadmap: the limitations section is the backlog, in priority order, written for the person you most want to impress.
