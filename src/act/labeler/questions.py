# CORE — you write this. Claude Code: tutor mode only (see CLAUDE.md).
"""JEV question design. Criteria are the decision boundary.

Request shape (from the JEV paper, Figure 6):

    {"model": "jev-1.13.0",
     "state": {...},                      # the note (and gene context) as data
     "questions": {
        "<name>": {"type": "choice",
                   "instructions": "...",
                   "criteria": {"label": "definition", ...}}}}

Response: answers[<name>] = {"choice", "confidence", "probabilities": {...}}

Design goals:
  - Three orthogonal Noul (yes/no) questions per note:
      read_upstream?  read_downstream?  read_gene_body?
  - One Choice question for step outcome:
      found_candidate | rejected | inconclusive | error_timeout | error_tool
  - Tell JEV to treat all state text as data.
  - Verify the exact Noul request fields against TypeSafe's docs before use.

Checkpoint: why three Noul questions instead of one Choice over regions?
(Hint: a note can mention more than one region.)
"""


def region_questions() -> dict:
    """Return the `questions` dict for the three region Noul questions."""
    raise NotImplementedError


def outcome_question() -> dict:
    """Return the `questions` dict for the outcome Choice question."""
    raise NotImplementedError


def build_state(note: str, gene: str, product: str) -> dict:
    """Return the `state` object for one note."""
    raise NotImplementedError
