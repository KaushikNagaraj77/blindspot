# CORE — you write this. Claude Code: tutor mode only (see CLAUDE.md).
"""Question design for the local zero-shot labeler (labeler/zeroshot.py).
Your hypotheses and definitions are the decision boundary.

Question shapes (see zeroshot.py for how each is scored):

    {"<name>": {"type": "binary", "hypothesis": "<positive statement>"}}
        -> {"choice": "yes"|"no", "probabilities": {"yes": p, "no": 1 - p}}

    {"<name>": {"type": "choice", "criteria": {"<label>": "<definition>", ...}}}
        -> {"choice": "<label>", "probabilities": {...}}   # sums to 1

Design goals:
  - Three orthogonal binary questions per note:
      read_upstream?  read_downstream?  read_gene_body?
  - One choice question for step outcome:
      found_candidate | rejected | inconclusive | error_timeout | error_tool
  - Phrase hypotheses as positive statements (no "did not ...").
  - The premise is the text the model reads. Everything in it can sway the
    scores, so include only what helps the decision.

Checkpoint: why three binary questions instead of one choice over regions?
(Hint: a note can mention more than one region.)
"""


def region_questions() -> dict:
    """Return the `questions` dict for the three region binary questions."""
    raise NotImplementedError


def outcome_question() -> dict:
    """Return the `questions` dict for the outcome choice question."""
    raise NotImplementedError


def build_premise(note: str, gene: str, product: str) -> str:
    """Return the premise text the classifier reads for one note."""
    raise NotImplementedError
