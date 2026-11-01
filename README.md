# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## What This Does

Provenance Guard is a small Flask service a writing site could call when someone
posts their work. It makes a guess about whether the text was AI-generated, says
how confident that guess is, shows the writer a plain-English label, and lets
them appeal.

**The path a submission takes:**

1. **Arrives at `POST /submit`** (`app.py::submit`) as JSON with `text` and `creator_id`.
2. **Gets checked.** Missing, empty or non-string `text` or `creator_id` → `400`;
   fewer than 10 words → `400`; more than 20,000 characters → `413`. Every
   refusal is still written to the audit log (`audit.log_rejection`) so nothing
   disappears without a trace.
3. **Signal one — the model signal** (`detector.py::model_signal`). GPT-2 runs
   locally and measures how predictable the text is (perplexity), squashed to a
   0–1 score where higher means more AI-like.
4. **Signal two — the style signal** (`stylometry.py::style_signal`). Measures
   the text's shape without reading it: sentence-length spread, vocabulary
   variety, expressive punctuation. Also 0–1, higher means more AI-like.
5. **Combined into one confidence score** (`scoring.py::combine_signals`): a
   weighted average, pulled toward "unsure" when the signals disagree, and
   capped below the AI line when the text is under 100 words.
6. **Mapped to a label** (`scoring.py::score_to_label`): one of three full
   sentences: likely AI, unsure, or written by a person.
7. **Logged and returned.** A new `content_id` is generated, the decision
   (both signal scores, the combined score, guess, label, status `decided`) is
   appended to `logs/audit.jsonl`, and the same fields come back as JSON. If the
   writer disagrees, `POST /appeal` with that `content_id` appends an appeal
   entry and moves the item to `under_review`.

**The contract**

`POST /submit`

| In | Type | Notes |
|---|---|---|
| `text` | string | required, 10+ words, ≤ 20,000 characters |
| `creator_id` | string | required, non-empty |

| Out (200) | Type | Notes |
|---|---|---|
| `content_id` | string | 12 hex chars; what `/appeal` needs |
| `guess` | string | `"ai"`, `"unsure"` or `"human"` |
| `confidence` | float 0–1 | the combined score; higher = more likely AI |
| `label` | string | the sentence the writer sees |
| `model_score` | float 0–1 | signal one |
| `style_score` | float 0–1 | signal two |
| `status` | string | always `"decided"` on a new submission |

Errors come back as `{"error": "<code>", "message": "<sentence>"}` with `400`,
`413`, or `503` (detector couldn't load).

`POST /appeal`

| In | Type | Notes |
|---|---|---|
| `content_id` | string | required; must match an earlier submission |
| `reasoning` | string | required, non-empty: the writer's explanation |

| Out (200) | Type | Notes |
|---|---|---|
| `content_id` | string | echoed back |
| `status` | string | `"under_review"` |
| `original_guess` | string | what the system had said |
| `message` | string | confirmation for the writer |

Unknown `content_id` → `404`; missing field → `400`. The original decision is
never overwritten: the log is append-only, so the decision and the appeal sit
side by side.

---

## Signals and Scoring

### Signal one — the model signal

**What it measures:** How predictable the text is to GPT-2 (perplexity over the
first 400 tokens), turned into 0–1 by a logistic curve centred on perplexity 45.
Low perplexity → high score → "more AI-like". I left the starter's midpoint
(45) and steepness (1.6) unchanged.

**Why that might differ between human and AI writing:** A language model writes
by choosing likely next words, so its output is text a language model finds easy
to predict. People make odder, more specific choices.

**What it can't see:** Who wrote it. Predictability isn't authorship. Plain
writing with common words in short sentences scores like AI. On my calibration
set, a plainly written human paragraph about Sunday cooking scored **0.887**,
almost identical to the clearly-AI paragraph (**0.898**). That's the writer most
likely to be falsely accused: someone writing in a second language, a younger
writer, anyone writing simply. The reverse hole: ornate or rare-word prose
(or AI text with odd words swapped in) reads as human.

### Signal two — the style signal

**What it measures:** The shape of the text, from three measures in
`stylometry.py`:

| Measure | What I compute | Mapped to "AI-ness" | Weight |
|---|---|---|---|
| `sentence_length_spread` | stdev ÷ mean of words per sentence | `1 − spread/0.6`, clipped 0–1 | 0.5 |
| `type_token_ratio` | moving-average TTR over 40-word windows | `(0.95 − mattr)/0.25`, clipped | 0.2 |
| `punctuation_density` | `; : ( ) ! ?` and dashes per word (commas/periods excluded) | `1 − density/0.05`, clipped | 0.3 |

`style_signal = 0.5·spread_ai + 0.2·ttr_ai + 0.3·punct_ai`

**Why that might differ between human and AI writing:** Generated prose tends to
march in even, mid-length sentences and use only "safe" punctuation. Human
writing is lumpier: a three-word sentence next to a forty-word one, a dash, a
question, an aside in parentheses.

**What it can't see:** Meaning. It can't read at all. Anything that changes the
shape without changing the substance moves it: splitting or merging sentences,
adding a few dashes or exclamation marks, pasting in a quotation, adding typos.
That's cheap to do on purpose. It also shares signal one's bias against plain
writers: short, even sentences with no fancy punctuation look "AI-ish" here too
(the Sunday-cooking paragraph scored **0.700**).

Vocabulary variety turned out to run *backwards* from the usual claim on my
samples: the clearly-AI paragraph had a high MATTR (0.925), and the plain human
paragraph had the lowest (0.784). That's why it only gets 0.2 of the weight.

### The combining rule

**The rule:**

1. Take a weighted average of the two signals, with the model signal counting more.
2. If the two signals are 0.4 or more apart, they're disagreeing, and I pull
   the score halfway back toward 0.5, because two methods disagreeing *is*
   uncertainty and it should land in "unsure", not on a side.
3. If the text is under 100 words, the score is capped at 0.69, just under the
   AI line. Short text can be "unsure" at worst, never accused.

**The numbers** (all in `config.py`):

| Setting | Value |
|---|---|
| `WEIGHT_MODEL_SIGNAL` | 0.6 |
| `WEIGHT_STYLE_SIGNAL` | 0.4 |
| `DISAGREEMENT_GAP` | 0.4 |
| `DISAGREEMENT_SHRINK` | 0.5 → `score = 0.5 + (score − 0.5) × 0.5` |
| `MIN_WORDS_FOR_AI_LABEL` | 100 (cap = `AI_THRESHOLD − 0.01` = 0.69) |
| `HUMAN_THRESHOLD` | 0.40 |
| `AI_THRESHOLD` | 0.70 |

**Where it lives:** `scoring.py::combine_signals`

**Calibration run** (both signals and the result, through the live service):

| Input | Words | model | style | combined | Label |
|---|---|---|---|---|---|
| Clearly AI (short) | 71 | 0.898 | 0.712 | 0.690 (capped) | unsure |
| Clearly AI (long) | 121 | 0.861 | 0.584 | 0.750 | **ai** |
| Clearly AI, remote-work essay | 120 | 0.738 | 0.608 | 0.686 | unsure |
| Lightly edited AI | 73 | 0.745 | 0.476 | 0.637 | unsure |
| Casual human (bus story) | 73 | 0.344 | 0.045 | 0.225 | **human** |
| Formal human (committee) | 51 | 0.378 | 0.357 | 0.369 | **human** |
| Plain human (Sunday cooking) | 62 | 0.887 | 0.700 | 0.690 (capped) | unsure |
| Casual but predictable human | 59 | 0.861 | 0.238 | 0.556 | unsure |

**A case where my two signals split, and what my rule does with it:** The
"casual but predictable" paragraph ("I went to the store and I got some milk…
My dog was happy to see me — he always is!"). Signal one says 0.861 (common
words, very predictable); signal two says 0.238 (sentence lengths vary, a dash
and an exclamation mark). They're 0.62 apart, so the disagreement rule fires:
the weighted average of 0.612 gets pulled to **0.556 → unsure**. That's what I
want. A person wrote it, and the system admits it can't tell instead of leaning
on the signal that happens to be loudest.

**What this costs:** the rule is conservative. A clearly generated 120-word
remote-work essay scored 0.686 and got "unsure", not "AI". I'd rather miss that
than accuse the Sunday-cooking writer. But the 100-word cap only protects
*short* plain writing. A long, plainly written human piece could still cross
0.70, and that's the false positive I expect next unit to find.

---

## Label Variants

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human | 0.00 – under 0.40 | We think this was written by a person. |
| unsure | 0.40 – under 0.70 | We couldn't tell who wrote this, so we're not making a call, and this is not an accusation. |
| high-confidence AI | 0.70 – 1.00 | Our system flagged this as possibly AI-assisted. This is an automated guess and it can be wrong. If you wrote this yourself, you can appeal and a person will review it. |

Every score from 0 to 1 falls in exactly one band. All three were reached in
the calibration run above.

**Why I worded the "unsure" one this way:** The person reading it probably wrote
every word, so it says outright that it isn't an accusation. It says "we
couldn't tell" (the system's limit) rather than "this might be AI" (a suspicion
about them). I cut it down to one sentence so people actually read it. The AI
label says "flagged as possibly AI-assisted" rather than "written with an AI
tool", calls itself a guess that can be wrong, and is the one that mentions
appealing, because a falsely accused writer is the one who'll read it.

---

## Sample Run

The service was run with `PORT=5001`, because macOS's AirPlay Receiver holds
port 5000 on my machine. Otherwise the commands are the same.

**A submission**

```bash
$ curl -X POST http://127.0.0.1:5001/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "Artificial intelligence has transformed the way we live and work. It offers numerous benefits, including increased efficiency, improved decision-making, and enhanced productivity. However, it is important to consider the potential challenges as well. Organizations must ensure that their systems are fair, transparent, and accountable. By addressing these concerns, we can harness the full potential of this technology. Ultimately, the future of artificial intelligence depends on our ability to use it responsibly. In addition, effective implementation requires collaboration between stakeholders across multiple sectors. Governments, businesses, and educational institutions all play a crucial role in shaping policies that promote innovation while protecting individual rights. Furthermore, ongoing research and continuous evaluation are essential to ensure that these systems remain safe and beneficial over time.", "creator_id": "writer_042"}'
```

```json
{
    "confidence": 0.7498,
    "content_id": "e9ccdcb52ab6",
    "guess": "ai",
    "label": "Our system flagged this as possibly AI-assisted. This is an automated guess and it can be wrong. If you wrote this yourself, you can appeal and a person will review it.",
    "model_score": 0.8605,
    "status": "decided",
    "style_score": 0.5838
}
```

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5001/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "e9ccdcb52ab6", "reasoning": "I wrote this myself for my policy class. I write in a formal style because that is how we were taught to write essays."}'
```

```json
{
    "content_id": "e9ccdcb52ab6",
    "message": "Thanks \u2014 your appeal is recorded. A person will review this piece, and the automated label won't be treated as final while they do.",
    "original_guess": "ai",
    "status": "under_review"
}
```

**What the log shows afterwards** (the third entry is a separate short submission I sent to check the new "unsure" wording)

```bash
$ curl "http://127.0.0.1:5001/log?limit=3"
```

```json
{
    "count": 3,
    "entries": [
        {
            "combined_score": 0.7498,
            "content_id": "e9ccdcb52ab6",
            "creator_id": "writer_042",
            "guess": "ai",
            "label": "Our system flagged this as possibly AI-assisted. This is an automated guess and it can be wrong. If you wrote this yourself, you can appeal and a person will review it.",
            "model_score": 0.8605,
            "status": "decided",
            "style_score": 0.5838,
            "timestamp": "2026-11-01T23:43:18+00:00",
            "word_count": 122
        },
        {
            "content_id": "e9ccdcb52ab6",
            "creator_id": "writer_042",
            "event": "appeal",
            "reasoning": "I wrote this myself for my policy class. I write in a formal style because that is how we were taught to write essays.",
            "status": "under_review",
            "timestamp": "2026-11-01T23:43:18+00:00"
        },
        {
            "combined_score": 0.69,
            "content_id": "e7b846284612",
            "creator_id": "label_check",
            "guess": "unsure",
            "label": "We couldn't tell who wrote this, so we're not making a call, and this is not an accusation.",
            "model_score": 0.8548,
            "status": "decided",
            "style_score": 0.6309,
            "timestamp": "2026-11-01T23:43:18+00:00",
            "word_count": 34
        }
    ]
}
```

**Bad input, for the record:**

```text
{"creator_id":"x"}                          -> 400 {"error":"missing_text", ...}
{"text":"   ","creator_id":"x"}             -> 400 {"error":"missing_text", ...}
{"text":"too short","creator_id":"x"}       -> 400 {"error":"text_too_short", ...}
{"text":"hello there friend ... ok"}        -> 400 {"error":"missing_creator_id", ...}
[1,2]                                       -> 400 {"error":"body_not_json_object", ...}
not json                                    -> 400 {"error":"body_not_json_object", ...}
25,000-character text                       -> 413 {"error":"text_too_long", ...}
/appeal {"content_id":"nope", ...}          -> 404 {"error":"unknown_content_id", ...}
/appeal {"content_id":"nope"}               -> 400 {"error":"missing_reasoning", ...}
```

---

## How I Used AI

I used Claude Code as a coding assistant on this project. The two moments below
are where I made the call.

**Moment 1: the label wording**

- *What I asked for:* Help building the service from the brief: the style
  signal, the combining rule, and the two routes, including first drafts of the
  three labels.
- *What came back:* Working code, plus a calibration table that showed my plain
  human test paragraph scoring 0.887 on signal one, as AI-like as real AI text.
  The draft labels were long, and the AI one said the piece was "likely written
  with an AI tool".
- *What I changed:* I rewrote two of the labels. I cut the "unsure" label down
  to one sentence ("We couldn't tell who wrote this, so we're not making a call,
  and this is not an accusation.") because a long hedge is easy to skim past. I
  softened the AI label to "flagged this as possibly AI-assisted", because the
  calibration table showed real human writing can score as high as AI, so the
  label shouldn't read like a verdict.

**Moment 2: the acceptance criteria**

- *What I asked for:* I asked for my five acceptance criteria to be written for me.
- *What came back:* It declined to write them, because the brief says criteria
  must be my own. Instead it laid out options for each target and what each
  choice would mean (for example 0, 1 or 2 false positives out of 10, and a
  score gap of 0.30, 0.40 or 0.50).
- *What I changed:* I chose the targets myself: at most 1 of 10 of my own pieces
  called AI, 9 of 10 appeals recorded, a 0.40 gap between clear AI and clear
  human text, and at most 1 of 5 short plain pieces called AI.

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** ___ per minute, ___ per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

**What a caller counts as:** <!-- per address, or per creator_id? They fail
differently — one script can look like a thousand callers, and one household
can look like one. -->

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```

```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
