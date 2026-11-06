# SkillTrack AI

**A career-readiness platform for engineering students.**
SkillTrack AI analyses a resume, measures skills with quizzes, computes the gap
to a chosen career, ranks suitable careers and builds a week-by-week learning
roadmap — all with free and open-source tools, and without any paid API.

> Final-year B.Tech (AI & ML) project.
> Stack: Flask · MySQL 8 · scikit-learn · spaCy · PyMuPDF · Bootstrap 5 · Chart.js

---

## 1. What it does

A student creates an account, states their interests and selects a career. The
system then combines three independent evidence sources:

| Source | How it is measured | Weight |
|--------|--------------------|--------|
| **Self assessment** | Student rates each skill 0–5 | 0.30 |
| **Resume** | NLP extraction from an uploaded PDF | 0.30 |
| **Quiz** | Generated assessment, accuracy mapped to a level | 0.40 |

The weights are renormalised over whichever sources exist, so a student who has
not uploaded a resume is still scored on self-assessment and quizzes. Missing
evidence is never treated as zero ability.

### The 12 modules

1. **Authentication** — register, login, logout, hashed passwords, CSRF,
   session lockout after repeated failures.
2. **Student profile** — branch, year, interests, weekly study hours, skill
   self-assessment, profile completeness.
3. **Career selection** — eight predefined career paths with weighted skill
   requirements.
4. **Resume analyzer** — PDF upload, text extraction, alias + fuzzy skill
   detection, evidence-based level scoring, match percentage, history.
5. **Skill assessment** — one-skill quiz with MCQ, output, coding and scenario
   questions; optional Ollama generation, deterministic offline fallback.
6. **Gap analyzer** — per-skill gap and weighted readiness for any career.
7. **Personalized roadmap** — prerequisite-aware DAG, weekly schedule, free
   resources, progress tracking that survives regeneration.
8. **AI quiz generator** — local Ollama first, template generator otherwise;
   generated questions are capped at level 3.0 unless the skill has a validated
   bank.
9. **Performance analysis** — score trend, skill accuracy, readiness comparison
   and a reconstructed readiness trend, with Chart.js.
10. **Student dashboard** — readiness banner, best career matches, next steps,
    recent activity.
11. **Admin dashboard** — student list, activation/deactivation, platform
    statistics.
12. **Career recommendation** — hybrid TF-IDF interest score + readiness,
    ranked with human-readable reasons.

---

## 2. Screens

| Route | Page |
|-------|------|
| `/` | Landing page (or dashboard when logged in) |
| `/login`, `/register` | Authentication |
| `/student/dashboard` | Student dashboard |
| `/student/profile` | Profile and skill self-assessment |
| `/student/careers` | Career catalogue and selection |
| `/student/gap` | Gap analysis and readiness |
| `/student/resume` | Resume upload and analysis history |
| `/student/recommendations` | Ranked career matches |
| `/student/roadmap` | Weekly learning roadmap |
| `/student/assessment` | Choose a skill to assess |
| `/student/assessment/<id>` | Take the quiz |
| `/student/assessment/<id>/result` | Result and answer review |
| `/student/performance` | Analytics dashboard |
| `/admin/` | Admin dashboard |
| `/admin/students` | Manage students |
| `/api/health` | Health check |
| `/api/student/performance` | Performance JSON |
| `/api/student/readiness` | Readiness JSON |

All student pages require login; admin pages require the admin role; guest
access to protected routes redirects to `/login`.

---

## 3. Architecture

The code is split into four layers so the algorithms can be tested without
Flask or MySQL:

```
app/          HTTP layer        routes, decorators, request validation, responses
services/     business logic    orchestration, scoring, roadmap, quiz lifecycle
ml/           algorithms        skill extraction, TF-IDF, templates, text utils
models/       data access       one repository per table group, SQL only
```

Rules enforced throughout:

* `ml/` imports no Flask and no SQL.
* `services/` imports no Flask and executes no SQL directly.
* `models/` contains SQL but no business decisions.
* `app/` handles HTTP concerns only.

```
Request → app/ route → services/ → ml/ + models/ → MySQL
```

---

## 4. Algorithms

| ID | Algorithm | Location | Summary |
|----|-----------|----------|---------|
| A1 | Resume skill extraction | `ml/skill_extractor.py` | Normalise text → split sections → exact alias matching with word boundaries → fuzzy fallback (rapidfuzz, cutoff 88) → evidence scoring 0–5 |
| A2 | Quiz level mapping | `services/skill_service.py` | Accuracy → level bands 90/75/60/40, minimum 3 answered questions |
| A3 | Evidence fusion | `services/skill_service.py` | Weighted average of self/resume/quiz, renormalised over available sources |
| A4 | Gap & readiness | `services/gap_service.py` | `Gap = max(0, Required − Current)`; weighted readiness formula |
| A5 | Career recommendation | `ml/career_matcher.py` | TF-IDF interest coverage + readiness blend (0.60/0.40) |
| A6 | Roadmap generation | `services/roadmap_service.py` | Kahn topological sort by prerequisite, priority by weighted gap, greedy week packing |
| A7 | Question validity | `ml/quiz_templates.py` | Validated bank first, generated questions after, level cap 3.0 without a bank |

### Core formulas

```text
Gap(i) = max(0, Required(i) − Current(i))

Readiness = Σ W(i) · min(Current(i), Required(i))
            ─────────────────────────────────────── × 100
                    Σ W(i) · Required(i)
```

Edge cases handled explicitly:

* missing skill row → `Current = 0`, flagged as no evidence;
* `None`, `NaN`, `"abc"` → treated as 0, never crashes;
* negative or zero weight → requirement ignored;
* zero denominator → readiness 0.0 with a reason string;
* `Current > Required` → capped at `Required`.

### Resume level scoring

Base score from mention count:

| Mentions | Base level |
|----------|------------|
| 1 | 1.5 |
| 2–3 | 2.0 |
| 4–6 | 2.5 |
| > 6 | 3.0 |

Adjustments: `+0.5` per extra section, project usage or proficiency wording;
`−0.5` for beginner wording or a skills-list-only mention. Final value clamped
to `1.0–5.0`.

### Roadmap rules

* A prerequisite is always scheduled before its dependant.
* Among unlocked skills, the largest weighted gap goes first.
* A topic is never split across weeks.
* Hours = chosen resource `est_hours × 1.5` practice buffer (minimum 2.0 h).
* Topics are packed into the student's `weekly_hours`, up to 24 weeks.
* Regenerating a plan preserves completed topics.

---

## 5. Database

Eleven tables, created by `database/schema.sql`:

| Table | Purpose |
|-------|---------|
| `students` | Accounts, roles, profile, interests, weekly hours |
| `careers` | Eight career paths with descriptions and keywords |
| `skills` | 50-skill catalogue with categories |
| `career_skills` | Weighted requirements + prerequisite edges |
| `student_skills` | Self, resume, quiz and fused levels per student |
| `assessments` | Quiz attempts, status, score, awarded level |
| `questions` | Manual and generated question bank |
| `quiz_results` | Per-question answers and correctness |
| `learning_resources` | Free resources per skill and difficulty |
| `learning_progress` | Roadmap items, scheduled hours, completion |
| `resume_records` | Upload metadata, extracted text, detected skills |

Seed data includes 8 careers, 50 skills, 68 career-skill rows, 65 manual
questions, 63 learning resources and 9 demo accounts.

---

## 6. Setup (Windows, from scratch)

### Prerequisites

* Windows 10/11
* Python **3.11** (tested with 3.11.9)
* MySQL **8.x** installed and running (`MySQL80` service)
* PowerShell

### Step 1 — open the project

```powershell
cd D:\projects\CODE
```

### Step 2 — create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Optional spaCy model (12 MB, improves tokenisation; the app works without it):

```powershell
.\.venv\Scripts\python.exe -m spacy download en_core_web_sm
```

If the download fails, set `SPACY_ENABLED=false` in `.env`.

### Step 3 — create the MySQL user

The project ships `database/create_app_user.sql`, which creates a limited user
that can only access the `skilltrack_ai` database.

1. Open **MySQL Workbench** and connect as `root`.
2. Open `database/create_app_user.sql`.
3. Execute the whole file (`Ctrl + Shift + Enter`).

It creates:

```
user     : skilltrack_user
password : SkillTrack@2026
database : skilltrack_ai
```

If you prefer to use `root`, skip this step and put the root password in
`.env` instead.

### Step 4 — configure `.env`

```powershell
Copy-Item .env.example .env
notepad .env
```

Minimum values to set:

```ini
SECRET_KEY=<random 64-char hex string>
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=skilltrack_user
DB_PASSWORD=SkillTrack@2026
DB_NAME=skilltrack_ai
```

Generate a real secret key with:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Never commit `.env`; it is already in `.gitignore`.

### Step 5 — create and seed the database

```powershell
.\.venv\Scripts\python.exe database\init_db.py --reset
```

This creates the database, applies the 11-table schema and runs all seed files.
Seeds use `INSERT IGNORE`, so running the command again without `--reset` is
safe.

Verify:

```powershell
.\.venv\Scripts\python.exe database\init_db.py --check --validate
```

Expected output ends with:

```
Validation: OK
```

### Step 6 — run the application

```powershell
.\.venv\Scripts\python.exe run.py
```

Open <http://127.0.0.1:5000>.

If MySQL is down, the app still boots and shows a **503 Setup required** page
with the exact error and fix, instead of a stack trace.

---

## 7. Demo accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@skilltrack.local` | `Admin@123` |
| Student | `aarav.patil@skilltrack.local` | `Student@123` |
| Student | `sneha.kulkarni@skilltrack.local` | `Student@123` |
| Student | `rohan.deshmukh@skilltrack.local` | `Student@123` |
| Student | `priya.joshi@skilltrack.local` | `Student@123` |
| Student | `aditya.shinde@skilltrack.local` | `Student@123` |
| Student | `neha.pawar@skilltrack.local` | `Student@123` |
| Student | `karan.jadhav@skilltrack.local` | `Student@123` |
| Student | `tanvi.more@skilltrack.local` | `Student@123` |

Seeded students already have self-assessments, quiz history and roadmap
progress, so the dashboards are not empty on first login.

---

## 8. Commands

| Task | Command |
|------|---------|
| Run the app | `.\.venv\Scripts\python.exe run.py` |
| Run without auto-reload | `.\.venv\Scripts\python.exe run.py --no-reload` |
| Check database | `.\.venv\Scripts\python.exe database\init_db.py --check` |
| Check + validate | `.\.venv\Scripts\python.exe database\init_db.py --check --validate` |
| Rebuild database | `.\.venv\Scripts\python.exe database\init_db.py --reset` |
| Unit tests | `.\.venv\Scripts\python.exe -m pytest` |
| All evaluations | `.\.venv\Scripts\python.exe evaluation\run_all.py` |
| One evaluation | `.\.venv\Scripts\python.exe evaluation\a4_gap_readiness.py` |
| Compile check | `.\.venv\Scripts\python.exe -m compileall -q app ml models services database evaluation tests` |

Stop the server with `Ctrl + C`.

---

## 9. Testing and evaluation

### Unit tests

```
111 passed
```

### Evaluation suite

| ID | Area | Measured result |
|----|------|-----------------|
| A1 | Resume extraction | 73 TP, 0 FP, 0 FN; micro/macro P/R/F1 = 100% on 9 labelled CVs |
| A2 | Quiz mapping and grading | 18/18 boundaries, 14/14 grading cases |
| A3 | Evidence fusion | 1000 random cases, max error 0.000000 |
| A4 | Gap and readiness | 800 random matrices, max error 0.000000 |
| A5 | Career recommendation | Top-1 16/16, top-3 16/16, MRR 1.0000 |
| A6 | Roadmap | 200 DAGs + 300 schedules, 0 violations |
| A7 | Question validity | 69 active questions, 0 invalid; 200 templates, 0 invalid |

Full methodology, per-career tables and limitations:
**[`docs/EVALUATION.md`](docs/EVALUATION.md)**

> These are regression benchmarks on hand-built synthetic fixtures. They show
> that the formulas and invariants hold — **not** real-world accuracy on
> recruiters' CVs or measured learning outcomes. The evaluation document lists
> every threat to validity.

---

## 10. Configuration

All settings live in `config.py` and can be overridden in `.env`.

| Variable | Default | Meaning |
|----------|---------|---------|
| `SECRET_KEY` | dev key | Flask session signing key — change in production |
| `FLASK_ENV` | `development` | `development`, `testing`, `production` |
| `FLASK_DEBUG` | `1` | Auto-reload and debug pages |
| `DB_HOST` / `DB_PORT` | `127.0.0.1` / `3306` | MySQL server |
| `DB_USER` / `DB_PASSWORD` | `root` / empty | MySQL credentials |
| `DB_NAME` | `skilltrack_ai` | Database name |
| `DB_POOL_SIZE` | `5` | Connection pool size |
| `MAX_UPLOAD_MB` | `5` | Resume size limit |
| `OLLAMA_ENABLED` | `true` | Try local LLM for quiz generation |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `llama3.2:3b` | Local model name |
| `SPACY_ENABLED` | `true` | Use spaCy if installed |
| `LOG_LEVEL` | `INFO` | Log verbosity |

Scoring constants (fusion weights, quiz bands, readiness bands, roadmap limits,
recommendation gain) are in `config.py` and are documented in code comments.

### Optional Ollama

The app works fully without Ollama. To enable local LLM question generation:

```powershell
# install Ollama from https://ollama.com, then
ollama pull llama3.2:3b
```

The app probes `/api/tags` with a 60-second cache and a 12-second generation
timeout. On any failure it silently falls back to deterministic templates.

---

## 11. Project structure

```
D:\projects\CODE
├── app/
│   ├── __init__.py            app factory, blueprints, error handlers
│   ├── auth.py                register / login / logout
│   ├── student.py             dashboard, profile
│   ├── careers.py             career catalogue, gap, recommendations
│   ├── resume.py              upload, analyse, delete
│   ├── roadmap.py             plan, status update, regenerate
│   ├── assessment.py          quiz start, take, submit, result
│   ├── performance.py         analytics page
│   ├── admin.py               admin dashboard and student management
│   ├── api.py                 health / performance / readiness JSON
│   └── utils/                 decorators, responses, security, validators
├── services/
│   ├── skill_service.py       A2/A3 fusion and level mapping
│   ├── gap_service.py         A4 gap and readiness
│   ├── career_service.py      A5 orchestration
│   ├── resume_service.py      upload pipeline
│   ├── quiz_service.py        quiz lifecycle and grading
│   ├── roadmap_service.py     A6 DAG and scheduler
│   └── performance_service.py analytics payloads
├── ml/
│   ├── skill_aliases.py       alias dictionary (data only)
│   ├── text_utils.py          normalisation and sectioning
│   ├── skill_extractor.py     A1 extraction and evidence scoring
│   ├── career_matcher.py      A5 TF-IDF matcher
│   ├── quiz_templates.py      deterministic offline questions
│   └── quiz_generator.py      optional Ollama integration
├── models/                    SQL repositories (11 tables)
├── database/
│   ├── schema.sql             11-table DDL
│   ├── init_db.py             create / seed / check / validate
│   ├── create_app_user.sql    limited MySQL account
│   └── seed_*.sql             skills, careers, questions, resources, demo data
├── templates/                 Jinja2 templates (auth, student, admin, errors)
├── static/
│   ├── css/main.css           design system
│   ├── js/main.js             UI helpers
│   ├── js/performance.js      Chart.js dashboards
│   └── vendor/                Bootstrap 5.3.3 + Chart.js 4.4.3 (offline)
├── evaluation/                A1–A7 runnable measurement scripts
├── tests/                     111 pytest unit tests
├── docs/
│   ├── EVALUATION.md          methodology, results, limitations
│   └── MYSQL_SETUP.md         MySQL troubleshooting and password reset
├── uploads/resumes/           private resume storage (gitignored)
├── logs/app.log               rotating application log
├── config.py                  single source of truth for settings
├── run.py                     entry point
├── requirements.txt
└── .env.example
```

---

## 12. Security notes

* Passwords are hashed with Werkzeug PBKDF2-SHA256 (600,000 iterations).
* All forms and state-changing POSTs use a CSRF token.
* SQL uses parameterised queries everywhere; identifiers are whitelisted.
* Uploads are checked by extension, MIME type and `%PDF-` magic bytes, stored
  under a random name, and limited to 5 MB.
* Session cookies are `HttpOnly` and `SameSite=Lax`; set
  `SESSION_COOKIE_SECURE=true` behind HTTPS.
* Repeated failed logins trigger a short per-session cool-down.
* Students can only access their own records; admin routes require the admin
  role and return 403 otherwise.
* `.env`, uploads and logs are excluded from Git.

Before deploying publicly: change `SECRET_KEY`, use a dedicated database user,
enable HTTPS, disable `FLASK_DEBUG`, and serve through a production WSGI server.

---

## 13. Limitations

These are known and intentional, not hidden:

1. A1/A5 benchmarks are synthetic and written by the project author; they are
   regression tests, not field accuracy.
2. Only 16 of 50 skills have three or more manually validated questions. The
   other 34 use generated questions and are capped at level 3.0.
3. Quiz difficulty bands are a fixed policy, not psychometrically calibrated.
4. The performance page's readiness trend is a reconstruction that holds
   current self/resume levels fixed; the UI states this.
5. Recommendations are estimates, not employment predictions. The disclaimer
   appears wherever rankings are shown.
6. No user study or learning-gain experiment was conducted.
7. Tested on one Windows 11 machine; no load or concurrency testing.

---

## 14. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `MySQL rejected the login (1045)` | Wrong `.env` credentials | Set `DB_USER` / `DB_PASSWORD`; test with `mysql -u skilltrack_user -p` |
| `Cannot reach the MySQL server (2003)` | MySQL service stopped | `net start MySQL80` |
| `Database does not exist (1049)` | DB not created | `python database/init_db.py --reset` |
| Page shows **503 Setup required** | DB unreachable at startup | Fix credentials, restart the app |
| `ModuleNotFoundError` | Wrong interpreter | Use `.\.venv\Scripts\python.exe`, not global `python` |
| spaCy model missing | `en_core_web_sm` not installed | `python -m spacy download en_core_web_sm` or `SPACY_ENABLED=false` |
| Resume rejected as scanned | No extractable text (image-only PDF) | Upload a text-based PDF |
| Ollama questions missing | Ollama not running | Expected: templates are used automatically |
| Port 5000 already in use | Another process | Stop it, or change the port in `run.py` |

More MySQL detail: [`docs/MYSQL_SETUP.md`](docs/MYSQL_SETUP.md).

---

## 15. Documentation

* [`docs/EVALUATION.md`](docs/EVALUATION.md) — A1–A7 methodology, measured
  results, reproducibility, threats to validity.
* [`docs/MYSQL_SETUP.md`](docs/MYSQL_SETUP.md) — MySQL installation, user
  creation, password reset, troubleshooting.

---

## 16. Credits and licence

Built as an individual B.Tech (AI & ML) final-year project using only free and
open-source software:

* Flask (BSD-3-Clause)
* MySQL Community Server (GPLv2)
* scikit-learn (BSD-3-Clause)
* pandas (BSD-3-Clause), NumPy (BSD-3-Clause)
* spaCy (MIT)
* PyMuPDF (AGPL-3.0)
* rapidfuzz (MIT)
* Bootstrap (MIT), Chart.js (MIT)

No paid API, key or cloud service is required to run the project.

Copyright 2026 Devraj Arun Sodage. Licensed under the
[Apache License 2.0](LICENSE).
