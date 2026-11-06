# SkillTrack AI — Evaluation Report

This document describes **exactly what was measured**, how to reproduce it, and
what the measurements do **not** prove.

Every number below was produced by running the scripts in `evaluation/` against
the code in this repository on the machine described in
[Environment](#environment). No result is estimated, extrapolated or copied from
a paper. The only synthetic parts are the labelled fixtures themselves, and that
limitation is stated explicitly in
[Threats to validity](#threats-to-validity).

---

## 1. Summary

| ID | Area | What is verified | Measured result | Checks | Time |
|----|------|------------------|-----------------|--------|------|
| A1 | Resume skill extraction | Precision / recall / F1 on 9 labelled CVs, 7 false-positive guards, fuzzy ablation | Micro & macro P/R/F1 = **100%** (73 TP, 0 FP, 0 FN) | 19 | ~1.5 s |
| A2 | Quiz accuracy → level | Band boundaries, minimum-answer guard, monotonicity, answer grading | 18/18 boundary cases, 14/14 grading cases | 40 | ~0.8 s |
| A3 | Evidence fusion | Weighted average, renormalisation, bounds, monotonicity, idempotence | 1000 random cases, max error **0.000000** | 19 | ~0.6 s |
| A4 | Gap & readiness | Formula vs independent reference, edge cases, seeded data | 800 random matrices, max error **0.000000** | 16 | ~1.2 s |
| A5 | Career recommendation | Top-1 / top-3 / MRR on 16 labelled queries, hybrid score formula | Top-1 **16/16**, top-3 **16/16**, MRR **1.0000** | 16 | ~36.2 s |
| A6 | Roadmap | DAG ordering, cycle safety, week packing, overflow, resources | 200 DAGs + 300 schedules, 0 violations | 16 | ~1.6 s |
| A7 | Question validity | Structural validity of bank + generated questions, level caps | 69 active questions, **0 invalid**; 200 templates, 0 invalid | 12 | ~1.8 s |
| — | Unit tests | Pure engines, no database required | **111 passed** (31.8 s cold, 13.3 s warm) | 111 | ~13–32 s |

`evaluation/run_all.py` runs A1–A7 and prints this summary. Any failed invariant
makes the script exit non-zero, so the suite can be used in CI. Timings above
are from a cold first run; warm runs are faster (A5 drops from ~36 s to ~12 s).

---

## 2. How to reproduce

From the project root (`D:\projects\CODE`):

```powershell
# one-time setup
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe database\init_db.py --reset

# all evaluations
.\.venv\Scripts\python.exe evaluation\run_all.py

# a single module
.\.venv\Scripts\python.exe evaluation\a4_gap_readiness.py

# unit tests
.\.venv\Scripts\python.exe -m pytest
```

A1, A5 and A6 need the seeded database because they load the real skill and
career catalogue. A2, A3 and the unit tests run without MySQL. A4 and A7 need
MySQL for their database snapshot sections.

Randomised checks use fixed seeds (`20261106`), so repeated runs give identical
results on the same dependency versions.

---

## 3. A1 — Resume skill extraction

**Script:** `evaluation/a1_resume_extraction.py`
**Module under test:** `ml/skill_extractor.py`, `ml/skill_aliases.py`,
`ml/text_utils.py`

### Method

Nine hand-written CV texts cover the eight target careers plus one typo document.
Each fixture has an explicit set of expected canonical skill names. The real
extractor is run against the real 50-skill catalogue; a detection counts as a
true positive only when the canonical name is in the expected set.

Additional checks:

* **7 false-positive guards** — `javascript` must not trigger `java`, `excellent`
  must not trigger `Excel`, `restaurant` must not trigger `REST API Design`,
  `classification` alone must not trigger `Computer Vision`, etc.
* **2 level-discrimination cases** — a bare skills-list mention must score lower
  than repeated project usage with proficiency wording.
* **Fuzzy ablation** — the typo document is run with and without fuzzy matching.

### Results

| Document | TP | FP | FN | Precision | Recall | F1 |
|----------|----|----|----|-----------|--------|----|
| python_backend | 10 | 0 | 0 | 100% | 100% | 1.00 |
| data_analyst | 9 | 0 | 0 | 100% | 100% | 1.00 |
| data_scientist | 10 | 0 | 0 | 100% | 100% | 1.00 |
| ml_engineer | 9 | 0 | 0 | 100% | 100% | 1.00 |
| ai_engineer | 7 | 0 | 0 | 100% | 100% | 1.00 |
| web_developer | 7 | 0 | 0 | 100% | 100% | 1.00 |
| full_stack | 10 | 0 | 0 | 100% | 100% | 1.00 |
| cybersecurity | 7 | 0 | 0 | 100% | 100% | 1.00 |
| typo_fuzzy | 4 | 0 | 0 | 100% | 100% | 1.00 |
| **Total** | **73** | **0** | **0** | **100%** | **100%** | **1.0000** |

Fuzzy ablation on the typo document:

```
with fuzzy    : ['Deep Learning', 'PyTorch', 'Python', 'TensorFlow']
without fuzzy : ['Deep Learning', 'Python', 'TensorFlow']
fuzzy gains   : ['PyTorch']
```

The ablation also exposed a real bug during development: `"pytoch,"` was
tokenised with the trailing comma, so the fuzzy matcher skipped it. Tokenising
with `re.findall(r"[A-Za-z]+", text)` fixed the typo recovery.

### Interpretation

The extraction pipeline behaves as designed on canonical CV wording, and the
guards confirm that word-boundary matching prevents the most dangerous alias
collisions. The 100% score is **not** an estimate of accuracy on real CVs — see
[Threats to validity](#threats-to-validity).

---

## 4. A2 — Quiz accuracy → level and answer grading

**Script:** `evaluation/a2_quiz_mapping.py`
**Modules under test:** `services/skill_service.py`,
`services/quiz_service.py`

### Method

1. All five configured bands and their exact boundaries are tested
   (90/75/60/40), including negative accuracy, >100% accuracy, missing values
   and non-numeric input.
2. Monotonicity is checked across the full 0–100% range.
3. `grade_text` is tested on 14 hand-labelled answers covering:
   whitespace and punctuation, list/tuple formatting, numeric equivalence,
   case-insensitivity, keyword alternatives (`AES|RSA`), multi-keyword answers,
   empty answers and near-miss wrong answers.
4. MCQ grading and free-text question grading are tested separately.

### Results

* Bands strictly descending: **PASS**
* 18/18 mapping cases: **PASS** (including `2 answers → no level`,
  `3 answers → level awarded`)
* Monotonic across 0–100%: **PASS**
* Text grading: **14/14**
* MCQ grading: **3/3**
* Free-text question grading: **3/3**

The band rule is:

```text
accuracy >= 90 → 5.0
accuracy >= 75 → 4.0
accuracy >= 60 → 3.0
accuracy >= 40 → 2.0
otherwise      → 1.0
```

with fewer than `QUIZ_MIN_QUESTIONS = 3` answered questions producing **no
level** rather than a low level. This is deliberate: absence of evidence must
not be recorded as evidence of weakness.

---

## 5. A3 — Evidence fusion

**Script:** `evaluation/a3_fusion_consistency.py`
**Module under test:** `services/skill_service.py`

### Method

The fusion rule is a weighted average over the evidence sources that exist:

```text
current = Σ(w_s · level_s) / Σ(w_s)      over available sources
weights: self 0.30, resume 0.30, quiz 0.40
```

An independent reference implementation in the evaluation script recomputes the
result. The script checks:

* all 8 subsets of `{self, resume, quiz}` — weights must sum to 1 and the fused
  value must equal the reference;
* 1000 random cases with missing values, out-of-range values and NaN-like input;
* boundedness (result lies between the minimum and maximum source);
* monotonicity (raising one source never lowers the fused value);
* idempotence (three equal sources return that value);
* no evidence returns `(0.0, {})`;
* invalid strings and out-of-range values are clamped or treated as missing.

### Results

| Property | Result |
|----------|--------|
| Max absolute error vs reference (1000 cases) | **0.000000** |
| Weights sum to 1 in every non-empty case | 0 failures |
| Fused value inside source bounds | 0 violations |
| Monotonicity violations | 0 |
| Idempotence (0.0, 1.5, 2.5, 5.0) | 4/4 |
| No evidence → `(0.0, {})` | PASS |
| Clamping `(-3, 9, "2.5")` | PASS |
| Junk value treated as missing | PASS |

Example subsets:

```
self+resume      weights {self: 0.50, resume: 0.50}          fused 1.5
self+quiz        weights {self: 0.4286, quiz: 0.5714}        fused 2.7
resume+quiz      weights {resume: 0.4286, quiz: 0.5714}      fused 3.1
self+resume+quiz weights {self: 0.30, resume: 0.30, quiz: 0.40} fused 2.5
```

This proves the implementation matches its specification. It does not prove
that 30/30/40 are the best possible weights; that would require labelled
student outcomes, which this project does not have.

---

## 6. A4 — Gap and readiness formula

**Script:** `evaluation/a4_gap_readiness.py`
**Module under test:** `services/gap_service.py`

### Method

The specification defines:

```text
Gap(i)    = max(0, Required(i) − Current(i))

Readiness = Σ(W(i) · min(Current(i), Required(i)))
            ──────────────────────────────────────── × 100
                    Σ(W(i) · Required(i))
```

The script compares the implementation against an independent reference
implementation over:

* 7 explicit edge cases: empty matrix, all weights zero, all requirements zero,
  negative weight, current above required, one missing skill, invalid values;
* 800 randomised matrices with missing rows, `None`, `"abc"`, negative weights,
  requirements above 5 and current values above required;
* a projection check (closing the top-N gaps produces the expected new score);
* seeded database snapshots for the first three students and all eight careers.

### Results

| Check | Result |
|-------|--------|
| Max absolute readiness error (800 cases) | **0.000000** |
| Max absolute gap error (800 cases) | **0.000000** |
| Counted-row agreement | 0 mismatches |
| Status counts add up | 0 mismatches |
| Top gaps sorted by weighted gap | PASS |
| 7/7 edge cases | PASS |
| Projection matches reference | PASS |

Seeded student 2, all eight careers:

| Career | Readiness |
|--------|-----------|
| Data Analyst | 64.18% |
| Data Scientist | 52.65% |
| Python Developer | 39.49% |
| AI Engineer | 25.47% |
| Machine Learning Engineer | 25.06% |
| Cybersecurity Analyst | 8.00% |
| Web Developer | 7.65% |
| Full Stack Developer | 0.00% |

The 0% row is a legitimate result: the student has no evidence for any skill
required by that career, and the zero-denominator path is covered by an
explicit test.

---

## 7. A5 — Career recommendation

**Script:** `evaluation/a5_recommender.py`
**Module under test:** `ml/career_matcher.py`, `services/gap_service.py`

### Method

Part 1 — 16 interest statements (2 per career), each with a known expected
career. The TF-IDF interest matcher ranks all eight careers. Top-1 accuracy,
top-3 accuracy and mean reciprocal rank (MRR) are reported.

Part 2 — the hybrid ranker on real seeded data:

```text
score = w_readiness · readiness + w_text · interest
default weights: 0.60 / 0.40, renormalised if a signal is missing
```

The script recomputes every final score from its components, checks the blend
weights sum to 1, checks the ordering is deterministic, and runs an ablation of
readiness-only vs text-only vs hybrid ranking.

### Results

| Metric | Result |
|--------|--------|
| Top-1 accuracy | **16/16 (100.0%)** |
| Top-3 accuracy | **16/16 (100.0%)** |
| MRR | **1.0000** |
| Hybrid score formula (max error) | 0.0000 |
| Blend weights sum to 1 | 8/8 rows |
| Determinism across two calls | PASS |
| Calibration gain 1.0–4.0 keeps ranking | 4/4 |
| Empty / stopword-only query → 0 | PASS |
| Empty career list → `{}` | PASS |

Seeded student 2 (Aarav Patil):

| Rank | Career | Readiness | Interest | Final | Fit |
|------|--------|-----------|----------|-------|-----|
| 1 | Data Scientist | 52.65% | 57.42% | **54.56** | Possible fit |
| 2 | Data Analyst | 64.18% | 30.48% | **50.70** | Possible fit |
| 3 | AI Engineer | 25.47% | 61.98% | **40.07** | Possible fit |
| 4 | Machine Learning Engineer | 25.06% | 26.94% | 25.81 | Stretch goal |
| 5 | Python Developer | 39.49% | 0.00% | 23.69 | Stretch goal |
| 6 | Cybersecurity Analyst | 8.00% | 0.00% | 4.80 | Stretch goal |
| 7 | Web Developer | 7.65% | 0.00% | 4.59 | Stretch goal |
| 8 | Full Stack Developer | 0.00% | 0.00% | 0.00 | Stretch goal |

The ablation is informative: readiness-only would rank Data Analyst first, while
text-only would rank AI Engineer first. The hybrid takes both signals into
account and produces Data Scientist first for this student. That is the intended
behaviour of a blended ranker, not evidence that the ranking is objectively
correct.

---

## 8. A6 — Roadmap ordering and scheduling

**Script:** `evaluation/a6_roadmap.py`
**Module under test:** `services/roadmap_service.py`

### Method

1. **DAG ordering.** 200 random DAGs (3–15 skills, 55% chance of a prerequisite
   edge) are passed through Kahn's algorithm with a max-heap priority on
   weighted gap. Every skill must appear exactly once and every prerequisite
   must come before its dependant.
2. **Cycle safety.** A 3-cycle and a self-loop must not lose topics.
3. **Week scheduling.** 300 random cases with 1–18 topics and weekly budgets of
   4–16 hours. No topic may be split, no normal week may exceed the budget, and
   total scheduled hours must equal total requested hours.
4. **Explicit packing cases.** `6+4 → week 1, 8 → week 2, 3 → week 3`;
   a topic larger than the weekly budget gets its own week; 40 topics overflow
   the 24-week limit and are flagged.
5. **Resource selection** by current level (beginner / intermediate / advanced).
6. **Seeded DAG.** All eight career prerequisite graphs are ordered and checked.

### Results

| Check | Result |
|-------|--------|
| Every skill appears exactly once (200 graphs) | 0 failures |
| Prerequisite before dependent | 0 violations |
| Cycle safety (3-cycle + self-loop) | all 5 topics kept |
| Empty input → empty order | PASS |
| Week capacity respected | 0 violations |
| Scheduled hours = requested hours | 0 losses |
| No split topics | 0 |
| Week numbers never move backwards | 0 regressions |
| Explicit packing cases | 3/3 |
| Resource selection | 3/3 |
| Seeded 8-career DAG | 0 ordering violations |

The scheduler is deterministic and independent of wall-clock time; weeks are
ordinal (`Week 1`, `Week 2`, …) rather than calendar dates, so regenerating a
plan on a different day does not shift it.

---

## 9. A7 — Question validity

**Script:** `evaluation/a7_question_validity.py`
**Modules under test:** `ml/quiz_templates.py`, `models/question_model.py`,
`services/quiz_service.py`

### Method

Structural validation only — not question quality or difficulty:

* every active question has a known type, non-empty text, an explanation longer
  than 10 characters and a known source;
* MCQ rows have exactly four unique options and a valid `correct_option` index;
* free-text rows have a non-empty expected answer;
* `is_validated` agrees with `source` (manual = 1, generated = 0);
* the offline template generator is run for all 50 skills and checked for
  determinism, uniqueness and at least 3 questions per skill;
* the level-cap policy is verified: **fewer than 3 validated bank questions in
  the pool caps the awarded level at 3.0**, otherwise 5.0.

### Results

| Check | Result |
|-------|--------|
| Active questions checked | 69 |
| Invalid questions | **0** |
| Types | mcq 51, scenario 12, output 5, coding 1 |
| Sources | manual 65, template 4 |
| `is_validated` agrees with source | 0 wrong |
| Skills with ≥3 validated bank questions | **16 / 50** |
| Skills with 1–2 validated questions | 0 |
| Skills with 0 validated questions | **34 / 50** |
| Template questions generated (50 skills) | 200 |
| Invalid template questions | **0** |
| Minimum per skill | 4 |
| Deterministic generation | 0 mismatches |
| Duplicate text within a skill | 0 skills |
| Template texts repeated across skills | 45 (informational) |
| Level caps (0/1/2/3/5 validated) | 5/5 |

The 45 cross-skill duplicate texts are generic category questions such as
"Which of these is NOT a core concept?". They are **informational, not a
failure**: each quiz attempt is single-skill, so two skills' template questions
never appear in the same attempt. They are documented here so the limitation is
visible rather than hidden.

Only 16 of 50 skills have enough manually validated questions for the full
1–5 level band. The remaining 34 use generated questions and are therefore
capped at level 3.0. This is a deliberate honesty mechanism: the system refuses
to award an expert-level score on the basis of unvalidated generated items.

---

## 10. Unit test suite

**Command:** `.\.venv\Scripts\python.exe -m pytest`

```
111 passed in 31.76s on the first cold run (13.33s warm).
```

| File | Coverage |
|------|----------|
| `tests/test_gap_service.py` | Gap formula, clamping, readiness, bands, projection |
| `tests/test_skill_service.py` | Effective weights, fusion, quiz level mapping, strength labels |
| `tests/test_quiz_engine.py` | Text grading, MCQ grading, pool selection, template generation |
| `tests/test_roadmap_engine.py` | DAG ordering, cycles, week packing, overflow, resources |
| `tests/test_career_matcher.py` | TF-IDF scores, blend weights, rank formula |
| `tests/test_skill_extractor.py` | Alias matching, boundaries, fuzzy typo, level scoring |

The tests are database-free by design (except where they exercise pure
functions), so they run on any machine after `pip install -r requirements.txt`.
The evaluation scripts cover the database-backed paths.

---

## 11. Threats to validity

These are the honest limits of the numbers above. They should be carried into
the report and the viva, not hidden.

1. **Synthetic labelled data.** The nine CVs in A1 and the 16 interest
   statements in A5 were written by the project author. They use the same
   canonical vocabulary as the alias dictionary and career keyword lists. A
   100% score therefore demonstrates **regression safety and internal
   consistency**, not field accuracy.
2. **No real-world CV corpus.** No public resume dataset with skill-level
   annotations was used. Real CVs contain layout noise, tables, images,
   non-English text and unusual synonyms that the fixtures do not model.
3. **Circularity in A5.** TF-IDF learns term weights from the career
   descriptions and keywords, and the test queries deliberately use those
   terms. The benchmark shows the matcher can recover the intended career from
   a clear interest statement; it does not show that the matcher understands
   ambiguous or contradictory interests.
4. **No difficulty calibration.** Quiz bands are a fixed policy
   (90/75/60/40), not item-response-theory or Rasch-calibrated thresholds. No
   psychometric validation was performed.
5. **Generated questions are not expert-validated.** 34 of 50 skills rely on
   template generation, and those quizzes are capped at level 3.0. The cap is a
   guardrail, not a substitute for a validated item bank.
6. **Algorithm tests are not educational-outcome tests.** A3, A4 and A6 prove
   that the code matches its specification. They do not prove that the
   readiness score predicts employability, that the roadmap improves learning,
   or that the recommender matches a human counsellor.
7. **No user study.** No students used the system in a controlled trial; there
   is no pre/post learning gain, no satisfaction survey and no A/B comparison.
8. **Readiness trend is reconstructed.** The performance page replays historical
   quiz levels while holding current self/resume levels fixed. It is explicitly
   labelled in the UI as a reconstruction, not a historical record.
9. **Single-machine evaluation.** All runs were on one Windows 11 laptop with
   local MySQL. No concurrency, load, or multi-user stress test was performed.
10. **Fixed random seeds.** Randomised checks are reproducible by design, which
    also means they explore the same 1000/800/300 cases every run. They are not
    a fresh sample each time.

What **can** be claimed safely:

* The formulas are implemented exactly as specified, including edge cases.
* The scoring pipeline is deterministic and internally consistent.
* The extractor avoids the common alias collisions tested in A1.
* The roadmap never violates prerequisite order or splits a topic.
* The system degrades safely when evidence is missing.
* The level-cap policy prevents unvalidated questions from producing
  expert-level claims.

---

## 12. Environment

| Component | Version |
|-----------|---------|
| OS | Windows 11 |
| Python | 3.11.9 |
| Flask | 3.1.3 |
| scikit-learn | 1.9.1 |
| pandas | 2.3.3 |
| numpy | 2.4.6 |
| PyMuPDF | 1.28.2 |
| spaCy | 3.8.18 |
| MySQL | 8.0.46 |
| pytest | 8.4.2 |

All dependencies are free and open source. Ollama is optional; the evaluation
scripts do not require it and the quiz generator falls back to deterministic
templates when it is unavailable.

---

## 13. File map

```
evaluation/
├── common.py                  shared DB helpers and output formatting
├── a1_resume_extraction.py    A1 — precision/recall/F1, guards, fuzzy ablation
├── a2_quiz_mapping.py         A2 — bands, minimum answers, grading
├── a3_fusion_consistency.py   A3 — weighted-average properties
├── a4_gap_readiness.py        A4 — formula vs independent reference
├── a5_recommender.py          A5 — top-1/top-3/MRR, hybrid score checks
├── a6_roadmap.py              A6 — DAG ordering and week scheduling
├── a7_question_validity.py    A7 — bank and generated-question validity
└── run_all.py                 runs A1–A7 and prints the summary

tests/
├── conftest.py
├── test_gap_service.py
├── test_skill_service.py
├── test_quiz_engine.py
├── test_roadmap_engine.py
├── test_career_matcher.py
└── test_skill_extractor.py
```
