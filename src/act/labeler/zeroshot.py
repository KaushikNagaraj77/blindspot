"""Local zero-shot labeler (cached). Replaces the TypeSafe JEV API, whose
signups are paused. An NLI model scores how strongly the note entails a
hypothesis, which gives a real probability per label for the cascade.

Question shapes (built in questions.py):
    {"<name>": {"type": "binary", "hypothesis": "<statement>"}}
        -> probabilities {"yes": p, "no": 1 - p}, p = P(note entails statement)
    {"<name>": {"type": "choice", "criteria": {"<label>": "<definition>", ...}}}
        -> one softmax over the definitions (sums to 1)

Write binary hypotheses as positive statements. NLI models handle negation
badly: a "did not read upstream" option scored high on every note in testing.

Speed (CPU, macOS 13, 3 binary + one 5-label choice question): ~2 s/note one
at a time, ~0.8 s/note with ask_many batches of 16. Label in bulk with ask_many.

Each answer is {name: {"choice", "probabilities"}}, the shape cascade.py expects.
"""

from functools import cache

from act.config import CACHE_DIR, LABELER_MODEL
from act.labeler.cache import JsonlCache

_cache = JsonlCache(CACHE_DIR / "labeler.jsonl")


@cache
def _classifier(model: str):
    from transformers import pipeline  # slow import; only load when needed

    return pipeline("zero-shot-classification", model=model)


def ask(premise: str, questions: dict, model: str = LABELER_MODEL, classifier=None) -> dict:
    return ask_many([premise], questions, model, classifier)[0]


def ask_many(premises: list[str], questions: dict, model: str = LABELER_MODEL,
             classifier=None, batch_size: int = 16) -> list[dict]:
    """Label many notes. Cached ones are reused; the rest run in batches."""
    payloads = [{"model": model, "premise": p, "questions": questions} for p in premises]
    results = [_cache.get(pl) for pl in payloads]
    todo = [i for i, r in enumerate(results) if r is None]
    if not todo:
        return results

    clf = classifier or _classifier(model)
    batch = [premises[i] for i in todo]
    answers = [{} for _ in todo]
    for name, q in questions.items():
        if q["type"] == "binary":
            outs = clf(batch, candidate_labels=[q["hypothesis"]], hypothesis_template="{}",
                       multi_label=True, batch_size=batch_size)
        else:
            labels = list(q["criteria"])
            outs = clf(batch, candidate_labels=[q["criteria"][k] for k in labels],
                       hypothesis_template="{}", multi_label=False, batch_size=batch_size)
        for ans, out in zip(answers, outs, strict=True):
            if q["type"] == "binary":
                p = out["scores"][0]
                probs = {"yes": p, "no": 1 - p}
            else:
                by_def = dict(zip(out["labels"], out["scores"], strict=True))
                probs = {k: by_def[q["criteria"][k]] for k in labels}
            ans[name] = {"choice": max(probs, key=probs.get), "probabilities": probs}

    for i, ans in zip(todo, answers, strict=True):
        _cache.put(payloads[i], ans)
        results[i] = ans
    return results
