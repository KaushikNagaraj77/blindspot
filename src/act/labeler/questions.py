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
    """Return the `questions` dict for the three region binary questions.

    One hypothesis per region, each a positive statement. Scored
    independently, so a note that mentions two regions can answer yes twice.
    """
    return {
        "read_upstream": {
            "type": "binary",
            "hypothesis": (
                "The agent read sequence upstream of the gene, before its start codon."
            ),
        },
        "read_downstream": {
            "type": "binary",
            "hypothesis": (
                "The agent read sequence downstream of the gene, after its stop codon."
            ),
        },
        "read_gene_body": {
            "type": "binary",
            "hypothesis": (
                "The agent read inside the gene: its coding sequence, protein domains, "
                "residues or motifs."
            ),
        },
    }


def outcome_question() -> dict:
    """Return the `questions` dict for the outcome choice question.

    Mutually exclusive, so one `choice` question rather than several binary ones.
    """
    return {
        "outcome": {
            "type": "choice",
            "criteria": {
                "found_candidate": "The agent found something striking or unexpected.",
                "rejected": "The agent looked and found nothing of interest.",
                "inconclusive": "The agent could not tell whether anything was there.",
                "error_timeout": "The step timed out before finishing.",
                "error_tool": "A tool failed or returned an error.",
            },
        }
    }


def build_premise(note: str, gene: str, product: str) -> str:
    """Return the premise text the classifier reads for one note.

    Gene name and product are included as context, but kept short: every word
    in the premise can move the scores.
    """
    return f"Gene {gene} ({product}). Agent note: {note}"
