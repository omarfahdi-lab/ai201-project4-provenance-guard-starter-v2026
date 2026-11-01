# Acceptance criteria — Provenance Guard

Five criteria that say what "working" means for this service, written in unit 7
**before** you built it.

**All five are yours.** None are given.

An acceptance criterion names a number or something plainly observable. *"The
detector is accurate"* is an opinion — and perfect AI detection isn't possible
anyway, so it's an opinion about something nobody can deliver. *"Of 10 pieces I
wrote myself, at most 1 is labelled high-confidence AI"* is a criterion.

Under each, write a sentence or two on **why that target**. *"I allow at most 1
false positive in 10 because on a writing site a wrong accusation costs more
than a missed detection"* is a real answer.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## Pick numbers you can defend

**Cover at least three of these five areas.** They're prompts, not a form.

| Area | A question it could answer |
|---|---|
| False positives | How often may a human's writing get called AI? |
| Score spread | How far apart should clearly-AI and clearly-human text score? |
| Label coverage | Is every one of your three labels actually reachable? |
| The appeal path | Does an appeal always change status and always get recorded? |
| Bad input | What happens when `text` is missing, empty, or enormous? |

Two things worth knowing before you pick numbers:

- **The expensive mistake is one-sided.** Missing some AI text costs the site a
  little. Accusing a real writer costs that person a lot. A criterion that
  treats both errors as equally bad is describing a system nobody would ship.
- **Unit 8 tests across three trials, and the target has to hold across all
  three.** Your first signal runs a model, so identical input can score
  differently twice. A target of "at most 1 in 10" against trials of 2, 1, 2 is
  a **miss**.

---
## 1. My own writing is rarely called AI

I submit 10 pieces of writing I wrote myself (each 100+ words) to `POST /submit`.
**At most 1 of the 10** comes back with `"guess": "ai"`.

**Why this target:** On a writing site, wrongly telling a real writer their work
is AI costs them far more than letting some AI text through costs the site.
Detection is imperfect, so 0 isn't realistic, but more than 1 in 10 means one
in every handful of honest writers gets accused. My model signal already scored
a plain human paragraph at 0.887, as high as real AI text, so this is a real
risk and not a formality.

---

## 2. Bad input never crashes the service

I send `POST /submit` each of: a body with no `text`, `text` that is an empty or
whitespace-only string, `text` under 10 words, `text` over 20,000 characters,
and a body that isn't a JSON object. **Every one returns a 4xx (400, or 413 for
the oversized text) with a JSON `error` field, and none returns a 500.** Each
refusal also appears in `GET /log` as a `rejected` entry.

**Why this target:** Malformed input is the most common real failure, and next
unit's attack set will send it on purpose. A 500 tells the writer nothing, and a
refusal that leaves no log entry is an attack I could never see afterwards.

---

## 3. Appeals are recorded

I submit 10 texts, then send `POST /appeal` with each returned `content_id` and a
reason. **In at least 9 of the 10**, the response says `"status": "under_review"`
AND `GET /log` shows an appeal entry for that `content_id` after the original
decision, with the original decision entry unchanged.

**Why this target:** The appeal is the only thing a wrongly accused writer can
do about my system's mistake, so it has to work. If an appeal is lost, that
writer stays labeled with no record they ever objected.

---

## 4. Clear AI and clear human text score far apart

I submit 5 texts I'm confident are AI-generated and 5 I'm confident are
human-written (each 100+ words). **The average `confidence` of the AI group is
at least 0.40 higher than the average of the human group.**

**Why this target:** My bands are human below 0.40 and AI at 0.70 or above, so
0.30 is the bare minimum to get from one band to the other. A 0.40 gap means
clear cases sit comfortably inside their bands instead of at the edges, leaving
the unsure band for genuinely uncertain text.

---

## 5. Short, plain human writing isn't accused

I submit 5 pieces of plainly written human text, each under 100 words, with
short sentences, common words and little punctuation. **At most 1 of the 5**
comes back with `"guess": "ai"`.

**Why this target:** These are the writers both of my signals are biased
against: second-language writers, younger writers, anyone writing simply.
My combining rule caps text under 100 words below the AI threshold (0.69) for
exactly this reason, so this checks whether that cap actually protects them. I
allow 1 because the model signal can score the same text differently between
trials.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 8 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath, like this:

         ## 2. Uncertain cases land in the unsure band

         The system handles uncertain cases well.

         **Why this target:** ...

         > **Revised in unit 8:** Text I judged borderline scores between
         > 0.4 and 0.6 in at least 4 of 5 cases.
         >
         > **Why revised:** "well" gave me nothing to check. I couldn't
         > reach a verdict from it at all.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "At most 1 of 10 of my own pieces flagged as AI" → "at most 3
            of 10", because 1 of 10 turned out to be hard.

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
