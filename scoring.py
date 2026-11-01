"""
Turning two numbers into one, and one number into something a person can read.

Two functions live here.

`combine_signals` is where your false-positive decision from Milestone 1
actually gets made. Everything above it — the labels, the appeal path — is
downstream of a number this function produced.

`score_to_label` is where you stop writing for a machine and start writing for
a person. A score of 0.62 means nothing to a writer.

⚠️ Your README's **Signals and Scoring** section has to name the file and
function holding your combining rule. The grader checks your code against what
you claim, so that line should read `scoring.py::combine_signals`.
"""

import config


def combine_signals(model_score: float, style_score: float, word_count: int | None = None) -> float:
    """
    Combine two 0–1 signals into one 0–1 score. Higher means more likely AI.

    The rule, in three steps:

      1. Weighted average: 0.6 × model_score + 0.4 × style_score. The model
         signal gets more weight because it separated my clearly-AI and
         clearly-human calibration texts by more.
      2. Disagreement: if the two signals are 0.4 or more apart, the score is
         pulled halfway back toward 0.5. Two methods disagreeing is
         uncertainty, and uncertainty should land in "unsure", not on a side.
      3. Short text: under 100 words, the score is capped just below the AI
         threshold. Too little text to accuse anyone — the worst that can
         happen to a short piece is "unsure".

    Numbers live in config.py.
    """
    score = config.WEIGHT_MODEL_SIGNAL * model_score + config.WEIGHT_STYLE_SIGNAL * style_score

    if abs(model_score - style_score) >= config.DISAGREEMENT_GAP:
        score = 0.5 + (score - 0.5) * config.DISAGREEMENT_SHRINK

    if word_count is not None and word_count < config.MIN_WORDS_FOR_AI_LABEL:
        score = min(score, config.AI_THRESHOLD - 0.01)

    return round(min(max(score, 0.0), 1.0), 4)


LABEL_AI = (
    "Our system thinks this piece was likely written with an AI tool. This is an "
    "automated guess, not a final decision, and it can be wrong. If you wrote "
    "this yourself, you can appeal and a person will review it."
)
LABEL_HUMAN = "We think this was written by a person."
LABEL_UNSURE = (
    "We couldn't tell whether this was written by a person or with an AI tool, "
    "so we aren't making a call either way. This is not an accusation, and "
    "nothing about your post has changed."
)


def score_to_label(score: float) -> tuple[str, str]:
    """
    Turn a score into (guess, label_text).

        score >= AI_THRESHOLD     -> "ai"
        score <  HUMAN_THRESHOLD  -> "human"
        anything in between       -> "unsure"

    Every score from 0 to 1 lands in exactly one band, so all three are
    reachable as long as the combined score can move across the whole range.
    """
    if score >= config.AI_THRESHOLD:
        return "ai", LABEL_AI
    if score < config.HUMAN_THRESHOLD:
        return "human", LABEL_HUMAN
    return "unsure", LABEL_UNSURE


def label_ranges() -> list[tuple[str, str]]:
    """
    The score range each label covers. Your README needs these beside the
    label text — given to you so the numbers can't drift apart from config.py.
    """
    return [
        ("high-confidence human", f"0.00 – under {config.HUMAN_THRESHOLD:.2f}"),
        ("unsure", f"{config.HUMAN_THRESHOLD:.2f} – under {config.AI_THRESHOLD:.2f}"),
        ("high-confidence AI", f"{config.AI_THRESHOLD:.2f} – 1.00"),
    ]
