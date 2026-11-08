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

**My limits:** 5 per minute, 50 per day (on `POST /submit` only; set in
`config.py`, applied by the `@limiter.limit(...)` decorator on `app.py::submit`)

**Why those numbers and not others:**

- **5 a minute.** A real writer submits a piece, reads the label, maybe fixes a
  typo and sends it again. That's 1 or 2 requests in a minute, so 5 is more
  than double what an honest person needs. The starter's 10 a minute would
  let a script send 600 probes an hour, which is plenty to map where my 0.40
  and 0.70 lines sit.
- **50 a day.** Nobody posts 50 pieces of their own writing in a day. A
  script that wants to find my thresholds needs hundreds of variations of the
  same text (add a dash, split a sentence, resubmit). At 50 a day, 1,000
  probes take 20 days under one `creator_id`.
- **What it costs:** a writer who pastes the same piece 6 times in a minute
  while fiddling with it gets a 429 and has to wait. I think that's fine:
  the message says "try again shortly", and a minute is a short wait.

**What a caller counts as:** the `creator_id` in the request body, falling
back to the caller's IP address when there's no usable `creator_id`
(`app.py::rate_limit_key`). That's good for one writer behind a shared school
network: they don't use up their classmates' allowance. It's bad against a
script, because the script chooses its own `creator_id`. If it sends every
request under a new id, it never hits a limit at all. Every row in the attack
set's `attacks.csv` does exactly that, which is why only the
`flood_same_creator` rows can be limited. A real fix needs a limit tied to
something the caller can't make up: a logged-in account, or a second,
looser limit per IP address on top of the per-creator one.

**The run of status codes when I pushed past it** (`python run_attacks.py
--flood 15`, written to `results/flood_2026-11-08_1819.md`):

```
200 200 200 200 200 429 429 429 429 429 429 429 429 429 429
```

The first 5 got through, and all 10 after that were refused. Each refusal is
in the audit log:

```json
{"timestamp": "2026-11-08T23:19:33+00:00", "creator_id": "flood_tester", "event": "rejected", "status": "rejected", "reason": "rate_limited", "limit": "5 per 1 minute"}
```

---

## Attack Run — Before

`python run_attacks.py --set attack_set --label before`, run once over all 56
inputs with rate limiting on and nothing else changed. Raw output:
`results/attack_run_2026-11-08_1821_before.md`.

**How I marked held or broke.** Each family is after something different, so
the rule depends on the family:

| Family | The attack wants | BROKE when |
|---|---|---|
| `evasion` (AI text) | AI text not to be flagged | `guess` is anything other than `ai`, because "unsure" isn't a flag either |
| `false_positive` (human text) | real writing to be called AI | `guess` is `ai` |
| `prompt_injection` | the service to do what the text says | the output matches what the instruction asked for, or the label or log was changed |
| `malformed`, `flood_same_creator` | a crash, a 500, a wrong answer, or no limit | 5xx, no JSON error, no log entry, a wrong refusal, or no 429 |

**One control, so the evasions can be judged fairly.** Every evasion row is the
same AI paragraph about workplace communication with one trick applied. I sent
that paragraph once with **no** trick applied (`creator_id: control_base_ai`):
model 0.669, style 0.666, combined **0.668 → unsure**. My service doesn't flag
this AI text even without any evasion. That matters for the diagnosis below.

| ID | Family | Targeting | Status | Guess | model | style | Score | Verdict |
|---|---|---|---|---|---|---|---|---|
| EV01 | evasion | signal two: typos raise word variety | 200 | unsure | 0.164 | 0.666 | 0.432 | **BROKE** |
| EV02 | evasion | signal two: broken-up sentences raise length spread | 200 | unsure | 0.594 | 0.133 | 0.455 | **BROKE** |
| EV03 | evasion | signal two: a pasted quotation changes the shape | 200 | unsure | 0.666 | 0.317 | 0.527 | **BROKE** |
| EV04 | evasion | signal one: unusual words raise perplexity | 200 | unsure | 0.611 | 0.655 | 0.629 | **BROKE** |
| EV05 | evasion | both signals: heavy human editing pass | 200 | human | 0.321 | 0.289 | 0.308 | **BROKE** |
| EV06 | evasion | signal two: one very long sentence and one very short | 200 | unsure | 0.573 | 0.346 | 0.482 | **BROKE** |
| EV07 | evasion | signal two: padding with punctuation | 200 | unsure | 0.586 | 0.569 | 0.579 | **BROKE** |
| EV08 | evasion | signal one: text below the token window | 200 | human | 0.245 | 0.564 | 0.373 | **BROKE** |
| EV09 | evasion | both: AI text with a human opening paragraph bolted on | 200 | unsure | 0.704 | 0.410 | 0.587 | **BROKE** |
| EV10 | evasion | signal two: repeated stanza structure | 200 | unsure | 0.979 | 0.672 | 0.690 (capped) | **BROKE** |
| FP01 | false_positive | plain, clear human writing with no flourishes | 200 | unsure | 0.618 | 0.515 | 0.577 | HELD |
| FP02 | false_positive | human writing in a formal register | 200 | unsure | 0.739 | 0.724 | 0.690 (capped) | HELD (only by the cap) |
| FP03 | false_positive | a non-native English speaker writing carefully | 200 | unsure | 0.805 | 0.607 | 0.690 (capped) | HELD (only by the cap) |
| FP04 | false_positive | a student essay written to a rubric | 200 | unsure | 0.833 | 0.574 | 0.690 (capped) | HELD (only by the cap) |
| FP05 | false_positive | technical documentation written by a person | 200 | unsure | 0.801 | 0.769 | 0.690 (capped) | HELD (only by the cap) |
| FP06 | false_positive | a person imitating a formal template | 200 | unsure | 0.881 | 0.499 | 0.690 (capped) | HELD (only by the cap) |
| FP07 | false_positive | human writing that repeats a phrase deliberately | 200 | unsure | 0.882 | 0.500 | 0.690 (capped) | HELD (only by the cap) |
| FP08 | false_positive | very short genuine human submission | 400 `text_too_short` | — | — | — | — | HELD (not accused, but refused) |
| PI01 | prompt_injection | instruction to ignore the check | 200 | unsure | 0.463 | 0.320 | 0.406 | HELD |
| PI02 | prompt_injection | instruction disguised as a system message | 200 | human | 0.204 | 0.167 | 0.189 | **BROKE** |
| PI03 | prompt_injection | instruction wrapped in the writer's voice | 200 | unsure | 0.594 | 0.215 | 0.443 | HELD |
| PI04 | prompt_injection | attempt to make the label text hostile | 200 | unsure | 0.500 | 0.308 | 0.423 | HELD |
| PI05 | prompt_injection | attempt to inject into the audit log | 200 | unsure | 0.640 | 0.107 | 0.464 | HELD |
| PI06 | prompt_injection | instruction plus real human text | 200 | unsure | 0.558 | 0.524 | 0.545 | HELD |
| MF01 | malformed | text is only whitespace | 400 `missing_text` | — | — | — | — | HELD |
| MF02 | malformed | text is a single character | 400 `text_too_short` | — | — | — | — | HELD |
| MF03 | malformed | text is control characters | 400 `text_too_short` | — | — | — | — | HELD |
| MF04 | malformed | text is only punctuation | 400 `text_too_short` | — | — | — | — | HELD |
| MF05 | malformed | text is a very long single word | 400 `text_too_short` | — | — | — | — | HELD |
| MF06 | malformed | text is emoji only | 400 `text_too_short` | — | — | — | — | HELD |
| MF07 | malformed | text is right-to-left script | 400 `text_too_short` (counted 0 words) | — | — | — | — | **BROKE** (wrong refusal) |
| MF08 | malformed | text is 60,000 characters | 413 `text_too_long` | — | — | — | — | HELD |
| RQ01 | malformed | no text field at all | 400 `missing_text` | — | — | — | — | HELD |
| RQ02 | malformed | no creator_id | 400 `missing_creator_id` | — | — | — | — | HELD |
| RQ03 | malformed | text is a number | 400 `missing_text` | — | — | — | — | HELD |
| RQ04 | malformed | text is a list | 400 `missing_text` | — | — | — | — | HELD |
| RQ05 | malformed | text is null | 400 `missing_text` | — | — | — | — | HELD |
| RQ06 | malformed | creator_id is an object | 400 `missing_creator_id` | — | — | — | — | HELD |
| RQ07 | malformed | body is a JSON array, not an object | 400 `body_not_json_object` | — | — | — | — | HELD |
| RQ08 | malformed | body is unparseable JSON | 400 `body_not_json_object` | — | — | — | — | HELD |
| RQ09 | malformed | body is empty | 400 `body_not_json_object` | — | — | — | — | HELD |
| RQ10 | malformed | body is form-encoded, not JSON | 429 in the full run; **400** `body_not_json_object` alone | — | — | — | — | HELD (see note) |
| RQ11 | malformed | body is JSON claiming to be plain text | 429 in the full run; **400** `body_not_json_object` alone | — | — | — | — | HELD (see note) |
| RQ12 | malformed | deeply nested JSON | 400 `missing_text` | — | — | — | — | HELD |
| FL01_01–05 | flood_same_creator | 20 rapid submissions from one creator | 400 ×5 (`text_too_short`, 9 words) | — | — | — | — | HELD |
| FL01_06–12 | flood_same_creator | 20 rapid submissions from one creator | 429 ×7 | — | — | — | — | HELD |

**Count:** 56 attacks, **44 held, 12 broke.** No input crashed the service or
got a 500.

| Family | Attacks | Held | Broke |
|---|---|---|---|
| evasion | 10 | 0 | 10 |
| false_positive | 8 | 8 (6 of them only because of the short-text cap) | 0 |
| prompt_injection | 6 | 5 | 1 (PI02) |
| malformed | 20 | 19 | 1 (MF07) |
| flood_same_creator | 12 | 12 | 0 |

**Note on RQ10 and RQ11.** In the full run they came back 429, not 400. Neither
has a JSON `creator_id` the limiter can read, so both counted against my
machine's address. That address had already been used 5 times that minute by
the other rows without a usable `creator_id` (RQ02, RQ06, RQ07, RQ08, RQ09), so
the route never saw them. I re-sent each one on its own once the minute had
reset (`results/attack_run_2026-11-08_1822_before_RQ10_retest.md`,
`..._1823_before_RQ11_retest.md`), and both came back
`400 body_not_json_object`. So the route handles them. The log has a smaller
gap, though: the 429 entry for RQ10 says `"creator_id": "unknown"`, even though
the form body said `creator_id=attacker_RQ10`. That's because the 429 handler
only reads JSON bodies.

**Ten audit log entries from the run** (from `logs/audit.jsonl`):

```json
{"timestamp": "2026-11-08T23:21:23+00:00", "content_id": "b61176557130", "creator_id": "attacker_FP03", "guess": "unsure", "model_score": 0.8051, "style_score": 0.607, "combined_score": 0.69, "label": "We couldn't tell who wrote this, so we're not making a call, and this is not an accusation.", "status": "decided", "word_count": 83}
{"timestamp": "2026-11-08T23:21:23+00:00", "content_id": "02fb4c1422ee", "creator_id": "attacker_FP05", "guess": "unsure", "model_score": 0.8005, "style_score": 0.7692, "combined_score": 0.69, "label": "We couldn't tell who wrote this, so we're not making a call, and this is not an accusation.", "status": "decided", "word_count": 70}
{"timestamp": "2026-11-08T23:22:36+00:00", "content_id": "69a3bc82dd96", "creator_id": "control_base_ai", "guess": "unsure", "model_score": 0.6694, "style_score": 0.6661, "combined_score": 0.6681, "label": "We couldn't tell who wrote this, so we're not making a call, and this is not an accusation.", "status": "decided", "word_count": 85}
{"timestamp": "2026-11-08T23:21:23+00:00", "content_id": "d76de2ecad6b", "creator_id": "attacker_EV01", "guess": "unsure", "model_score": 0.1635, "style_score": 0.6661, "combined_score": 0.4323, "label": "We couldn't tell who wrote this, so we're not making a call, and this is not an accusation.", "status": "decided", "word_count": 85}
{"timestamp": "2026-11-08T23:21:23+00:00", "content_id": "1516855234ef", "creator_id": "attacker_EV10", "guess": "unsure", "model_score": 0.9792, "style_score": 0.6718, "combined_score": 0.69, "label": "We couldn't tell who wrote this, so we're not making a call, and this is not an accusation.", "status": "decided", "word_count": 78}
{"timestamp": "2026-11-08T23:21:23+00:00", "content_id": "671c1618fc28", "creator_id": "attacker_EV08", "guess": "human", "model_score": 0.2452, "style_score": 0.5643, "combined_score": 0.3728, "label": "We think this was written by a person.", "status": "decided", "word_count": 10}
{"timestamp": "2026-11-08T23:21:23+00:00", "content_id": "a9999391e15c", "creator_id": "attacker_PI02", "guess": "human", "model_score": 0.2044, "style_score": 0.1668, "combined_score": 0.1894, "label": "We think this was written by a person.", "status": "decided", "word_count": 45}
{"timestamp": "2026-11-08T23:21:23+00:00", "content_id": "2cea87d83da1", "creator_id": "attacker_PI05", "guess": "unsure", "model_score": 0.6401, "style_score": 0.1072, "combined_score": 0.4635, "label": "We couldn't tell who wrote this, so we're not making a call, and this is not an accusation.", "status": "decided", "word_count": 30}
{"timestamp": "2026-11-08T23:21:23+00:00", "creator_id": "attacker_MF07", "event": "rejected", "status": "rejected", "reason": "text_too_short", "http_status": 400, "word_count": 0}
{"timestamp": "2026-11-08T23:21:23+00:00", "creator_id": "unknown", "event": "rejected", "status": "rejected", "reason": "rate_limited", "limit": "5 per 1 minute"}
{"timestamp": "2026-11-08T23:21:23+00:00", "creator_id": "attacker_flood", "event": "rejected", "status": "rejected", "reason": "rate_limited", "limit": "5 per 1 minute"}
```

Why these: FP03 and FP05 are real writers whose scores sat at exactly the
0.69 cap. The control shows real AI text scoring *lower* than those human
pieces. EV01 is a 0.50 swing on signal one from typos alone. EV10 is AI text
held back only by my own cap. EV08 and PI02 are AI text labelled
**human**. PI05 shows the injected `"combined_score": 0.01` didn't reach the
log: the real score (0.4635) did, and the submitted text is never written to
the log at all. MF07 is an Arabic paragraph logged as **0 words**. The last two
are rejections: the 429 for RQ10, logged as `unknown`, and one of the seven
429s from the flood rows.

**The single worst outcome:** FP03, the non-native English speaker. Their
careful paragraph about their first month in a new country scored model 0.805
and style 0.607. That combines to **0.726**, which is over my 0.70 AI line and
higher than the actual AI paragraph (0.668). They saw "unsure" for one reason
only: the piece is 83 words, and my rule caps anything under 100 words at 0.69.
If they had written a little more, past 100 words, in the same plain
style, nothing would have capped that 0.726, and my service would have told
them it "flagged this as possibly AI-assisted". The same is true of FP02, FP04, FP05,
FP06 and FP07 (uncapped scores 0.729 to 0.788). Nothing in this run accused a
human, but six of the seven scored human pieces are one paragraph away from it.
That writer is exactly the person both my signals are biased against.

---

## Run Log and Verdicts

`python run_eval.py --label before`, three trials of every criterion with
nothing changed in between. Raw output: `results/run_2026-11-08_1832_before.md`.
The scenarios are in `scenarios.py`.

**What each criterion was run against**

| # | Scenario in `scenarios.py` | What's sent |
|---|---|---|
| 1 | `c1 my own writing` | 10 pieces of my own coursework, 114–219 words each: an ALCE reflection, a physics lab report, a UX redesign homework, a data-narrative plan, a podcast plan, a design-prototype write-up. Copied as written, typos included. Where one section was under 100 words, it's joined to the next section of the same assignment. |
| 2 | `c2 bad input` | 6 raw bodies: no `text`, `""`, whitespace only, 5 words, 25,000 characters, and a JSON array instead of an object |
| 3 | `c3 appeals` | 10 throwaway texts. `run_eval.py::appeal_check` appeals each `content_id`, then reads `GET /log` back |
| 4 | `c4 clear AI` + `c4 clear human` | 5 essays Claude wrote, unedited (111–122 words), and 5 of my own pieces from criterion 1 |
| 5 | `c5 short plain human` | 5 short pieces of mine, 54–84 words |

I added two things to the test harness, `run_eval.py`. Neither is in the
service. First, after every request it reads the newest audit-log entry, so
criterion 2 can check that each refusal was logged. Second, an `appeal`
scenario type (`appeal_check`) for criterion 3: it sends the appeal, then
checks that the response says `under_review`, that the log has an appeal
entry after the decision, and that the decision entry is byte-for-byte the
same as before. `scenarios.validate()` now accepts a list body, so "the body
isn't a JSON object" can be sent.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. My own writing is rarely called AI | ≤ 1 of 10 `guess: ai` | 1/10 | 1/10 | 1/10 | **MET** |
| 2. Bad input never crashes the service | 6 of 6 return 4xx + JSON `error` + a `rejected` log entry, 0 × 500 | 6/6 | 6/6 | 6/6 | **MET** |
| 3. Appeals are recorded | ≥ 9 of 10 `under_review` + appeal logged after an unchanged decision | 10/10 | 10/10 | 10/10 | **MET** |
| 4. Clear AI and clear human text score far apart | mean(AI) − mean(human) ≥ 0.40 | 0.243 | 0.243 | 0.243 | **MISSED** |
| 5. Short, plain human writing isn't accused | ≤ 1 of 5 `guess: ai` | 0/5 | 0/5 | 0/5 | **MET** |

**How I decided each one**

1. **MET, but only just.** Exactly one of my ten pieces was called AI in every
   trial: my lab report's introduction and conclusion, at 0.7235. The target
   allows 1, so it holds. A second piece, the lab report's procedure section,
   scored **0.6967**, which is 0.003 under the AI line. A second accusation
   would have been a miss, and I came that close to it.
2. **MET.** All 6 bodies returned 400 (or 413 for the long one) with an
   `error` field, and the newest log entry after each was `rejected` with the
   matching reason. No 500 in 18 requests.
3. **MET.** 30 of 30 appeals passed every check.
4. **MISSED.** The AI mean was 0.760 and the human mean 0.517, so the gap was
   0.243 in all three trials, against a target of 0.40. It isn't close.
5. **MET.** No short piece was called AI. The highest was 0.6037 (the lab
   conclusion again). That would have been "unsure" even without the 100-word
   cap, so the cap wasn't what saved them.

All three trials were identical to four decimal places on every criterion.
Neither signal has any randomness in it (GPT-2 runs in eval mode, and the
stylometry is arithmetic), so that's what I'd expect. It also means the
"three trials" can't show instability here. They show the result isn't a
one-off.

**Were any targets too low?** Criteria 2, 3 and 5 held with room to spare.
Criterion 3's "at least 9 of 10" allows a lost appeal, but losing even one
appeal means a wrongly accused writer has no record that they objected. I'd
tighten it to **10 of 10**. Criterion 5 held, but "at most 1 of 5 called AI"
is easy for text under 100 words, because my cap makes an AI label impossible
there. A target that tests the signals and not the cap would be **"at most 1
of 5 short plain pieces scores 0.60 or higher."** Against that, this run
scores 1 of 5 (0.6037), a bare pass.

**Real output from trial 1** (produced by `run_eval.py::main`, which calls
`POST /submit` → `app.py::submit`; full output in
`results/run_2026-11-08_1832_before.md`). There's one excerpt per criterion.
Criteria 1 and 4 show the pieces that decided the verdict.

Criterion 1: the accused piece, the near miss, and the lowest score:

```json
[
  {"status": 200, "guess": "ai", "confidence": 0.7235, "model_score": 0.7688, "style_score": 0.6555,
   "label": "Our system flagged this as possibly AI-assisted. This is an automated guess and it can be wrong. If you wrote this yourself, you can appeal and a person will review it.",
   "sent": "In this lab, We did an experiment that proved Newton’s second law of m",
   "log_entry": {"status": "decided", "content_id": "71ae5d147450", "guess": "ai", "combined_score": 0.7235}},
  {"status": 200, "guess": "unsure", "confidence": 0.6967, "model_score": 0.7271, "style_score": 0.6512,
   "label": "We couldn't tell who wrote this, so we're not making a call, and this is not an accusation.",
   "sent": "For the experiment, we set up a cart on a flat track and tied a string",
   "log_entry": {"status": "decided", "content_id": "5f1a9f08760b", "guess": "unsure", "combined_score": 0.6967}},
  {"status": 200, "guess": "human", "confidence": 0.199, "model_score": 0.1879, "style_score": 0.2157,
   "label": "We think this was written by a person.",
   "sent": "I chose to focus on Idea 1. Specific break Reminder, 2. Timer Customiz",
   "log_entry": {"status": "decided", "content_id": "156e1c01c9c2", "guess": "human", "combined_score": 0.199}}
]
```

Criterion 2: missing text, oversized text, and a non-object body:

```json
[
  {"status": 400, "guess": null, "confidence": null, "model_score": null, "style_score": null, "label": null,
   "sent": "{\"creator_id\": \"c2_missing_text\"}", "error_field": "missing_text",
   "log_entry": {"event": "rejected", "status": "rejected", "reason": "missing_text", "http_status": 400}},
  {"status": 413, "guess": null, "confidence": null, "model_score": null, "style_score": null, "label": null,
   "sent": "word word word word word word word word word word word word word word ", "error_field": "text_too_long",
   "log_entry": {"event": "rejected", "status": "rejected", "reason": "text_too_long", "http_status": 413}},
  {"status": 400, "guess": null, "confidence": null, "model_score": null, "style_score": null, "label": null,
   "sent": "[\"text\", \"creator_id\"]", "error_field": "body_not_json_object",
   "log_entry": {"event": "rejected", "status": "rejected", "reason": "body_not_json_object", "http_status": 400}}
]
```

Criterion 3: one submit followed by its appeal (`run_eval.py::appeal_check`):

```json
{"status": 200, "guess": "human", "confidence": 0.2089, "model_score": 0.1321, "style_score": 0.324,
 "label": "We think this was written by a person.",
 "sent": "This is appeal test submission number 1. It exists so that the service",
 "log_entry": {"status": "decided", "content_id": "afde3e31ee2d", "guess": "human", "combined_score": 0.2089},
 "content_id": "afde3e31ee2d", "appeal_http": 200, "appeal_status": "under_review",
 "log_has_appeal_after_decision": true, "decision_unchanged": true, "appeal_passed": true}
```

Criterion 4: one clear-AI essay and one of my pieces (all ten scores are in
the diagnosis below):

```json
[
  {"status": 200, "guess": "ai", "confidence": 0.811, "model_score": 0.921, "style_score": 0.6459,
   "sent": "Climate change represents one of the most pressing challenges facing h",
   "log_entry": {"status": "decided", "content_id": "239333b0f818", "guess": "ai", "combined_score": 0.811}},
  {"status": 200, "guess": "unsure", "confidence": 0.6967, "model_score": 0.7271, "style_score": 0.6512,
   "sent": "For the experiment, we set up a cart on a flat track and tied a string",
   "log_entry": {"status": "decided", "content_id": "f00d0e147b8c", "guess": "unsure", "combined_score": 0.6967}}
]
```

Criterion 5: the highest-scoring short piece:

```json
{"status": 200, "guess": "unsure", "confidence": 0.6037, "model_score": 0.5291, "style_score": 0.7156,
 "label": "We couldn't tell who wrote this, so we're not making a call, and this is not an accusation.",
 "sent": "This lab taught us that Newton’s Second Law is true because the more w",
 "log_entry": {"status": "decided", "content_id": "aa7e6dd0eab5", "guess": "unsure", "combined_score": 0.6037}}
```

**Diagnoses**

There are two patterns behind almost every failure, plus two one-off bugs.

**Pattern 1: signal two can't tell AI writing from plain human writing, and
it takes 40% of the score.** (Criterion 4's miss, the near miss on criterion 1,
and the six false-positive attacks that held only because of the cap.)

- *Stage:* signal two (`stylometry.py::style_signal`), then the combining rule
  (`scoring.py::combine_signals`), which gives it 0.4 of the weight.
- *Mechanism:* I split criterion 4's gap by signal. Signal one: AI mean 0.833,
  my writing 0.498, a gap of **0.336**. Signal two: AI 0.649, mine 0.546, a
  gap of only **0.103**. The combined gap is 0.6 × 0.336 + 0.4 × 0.103 =
  **0.243**, exactly what the run shows. Signal two is a coin weighted
  slightly toward "AI" for everybody. Breaking it into its three measures
  (0 = human-ish, 1 = AI-ish) shows why:

  | Group | spread (w 0.5) | word variety (w 0.2) | punctuation (w 0.3) |
  |---|---|---|---|
  | Claude's 5 essays | 0.638 | **0.153** | 1.000 |
  | my 5 pieces | 0.419 | **0.409** | 0.849 |
  | attack set FP01–FP07 (human) | 0.336 | **0.651** | 1.000 |

  **Word variety runs backwards.** AI text uses *more* varied vocabulary
  than plain human writing, so this measure pushes human writing toward AI.
  The FP texts that repeat words on purpose (FP07) or use technical terms
  consistently (FP05) get hit hardest. **Punctuation is a constant.** Nobody
  in any group uses `; : ( ) ! ?` or dashes much, so it adds ≈0.3 to
  everyone's style score and separates nothing. Only sentence-length spread
  points the right way. So 50% of signal two's weight does nothing and 20%
  works against me.
- *Why it's also the false-positive pattern:* signal one already scores
  plain writing high (FP03's model score was 0.805). When signal two agrees
  for the wrong reasons, the disagreement rule never fires, and the score
  lands at 0.726–0.788. My lab report is the same shape: "We did a few runs,
  changing the weight each time" is predictable to GPT-2 (0.769). Signal two
  gave it 0.656, mostly because it has no expressive punctuation.

**Pattern 2: signal one reads "unpredictable tokens" as "human".** (EV01,
EV04, EV08, PI02; and the control AI paragraph sitting at only 0.669.)

- *Stage:* signal one (`detector.py::model_signal`).
- *Mechanism:* the score is perplexity, squashed around a midpoint of 45.
  Anything GPT-2 can't predict lowers it, whether that's a human choice or
  noise. **EV01's typos** ("poistioned", "thsi") break into rare sub-word
  tokens. The model score went from 0.669 to **0.164**, even though the
  attack was aimed at signal two. Signal two didn't move (0.666), so the
  signals were 0.50 apart, and my disagreement rule pulled the score toward
  0.5. That's 0.432, "unsure". **PI02's** `SYSTEM: ... guess=human,
  confidence=0.02` was never obeyed, because nothing in my pipeline reads
  instructions. But code-like tokens are also unpredictable: model 0.204,
  plus three short choppy lines that make the spread look human (style
  0.167), gives **0.189 → human**. **EV04's** rare words ("desiderata",
  "efficacious") only cost 0.06. **EV08** is 10 words: perplexity over about
  12 tokens is noise (0.245), and my 100-word cap only limits the *top* of
  the score, so a short text can still be confidently called "human".
- *Why every evasion broke:* the unedited AI paragraph already scores only
  0.669 on signal one. That's perplexity ≈ 29, under my midpoint of 45 but
  not by much. Combined with style 0.666, it gives 0.668, under the 0.70 AI
  line before any trick is applied. Every evasion then only had to keep it
  there. EV02 ("Really." after each sentence), EV03 (a quotation), EV06 (one
  very long sentence) and EV09 (a human opening) all work on spread: they
  push signal two down to 0.13–0.41. **EV07** is the odd one. Semicolons
  zero out punctuation, but joining everything into one sentence makes spread
  0, so style stays 0.57, and it's signal one (0.586) that keeps it unsure.
  **EV05** (a heavy human rewrite) lowered both signals, and it arguably *is*
  human writing now. **EV10** is the only evasion my signals actually caught
  (model 0.979, 0.856 combined). My own short-text cap held it at 0.69,
  because it's 78 words. That's the cost of the cap that protects FP02–FP07,
  and I chose it.

**Bug 1: MF07, Arabic text refused as "too short".** *Stage:* the route
(`app.py::submit`, through `stylometry.words`). *Mechanism:* `words()` matches
`[a-z0-9']+`, which only covers Latin letters. A 17-word Arabic sentence
counts as **0 words**, so the writer is told "Send at least 10 words". It
doesn't crash, but the reason given is false. Any writer whose script isn't
Latin gets the same wrong refusal.

**Bug 2 (in the log, not an attack verdict): a 429 can lose the caller's
name.** *Stage:* the 429 handler in `app.py`. *Mechanism:* it reads
`creator_id` only from a JSON body. RQ10 sent a form body with
`creator_id=attacker_RQ10`, and the log says `"creator_id": "unknown"`. Someone
reconstructing a flood from the log couldn't tell who sent it.

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
