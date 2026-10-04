"""Score your region hypotheses against real simulator notes.

Run:  .venv/bin/python scratch/try_questions.py

Edit the hypotheses in src/act/labeler/questions.py, re-run, watch the numbers.
First run downloads a ~700MB model and takes a minute; after that it is cached.
"""

import sys

sys.path.insert(0, "src")

from act.labeler import zeroshot
from act.labeler.questions import region_questions

# Two notes per (region, style), taken from data/events/sim00.jsonl
NOTES = [
    ("upstream", "explicit", "Read the region upstream of g1378 (hypothetical protein) for context."),
    ("upstream", "explicit", "Checked the upstream flank of g1092, ~500 bp before the start."),
    ("upstream", "implicit", "Looked just before the start codon of g1282; promoter-like stretch there."),
    ("upstream", "implicit", "Scanned what precedes g1942 on its strand for anything odd."),
    ("downstream", "explicit", "Looked at the downstream flank after g1119 ends."),
    ("downstream", "explicit", "Read ~500 bp downstream of g647 to check neighbours."),
    ("downstream", "implicit", "Checked what follows the stop codon of g685."),
    ("downstream", "implicit", "Glanced past the end of g55 toward the next ORF."),
    ("gene", "explicit", "Inspected coding sequence of g382. Nothing unusual in the hypothetical protein domains."),
    ("gene", "explicit", "Read the gene body of g40 (hypothetical protein); domain looks typical."),
    ("gene", "implicit", "hypothetical protein in g303: residues line up with known family members."),
    ("gene", "implicit", "Went through g77 end to end; the catalytic motifs are intact."),
]

KEY = {"read_upstream": "upstream", "read_downstream": "downstream", "read_gene_body": "gene"}

qs = region_questions()
answers = zeroshot.ask_many([n for _, _, n in NOTES], qs)

print(f"\n{'truth':12} {'style':9} {'up':>6} {'down':>6} {'gene':>6}   result")
print("-" * 62)
right = 0
for (truth, style, _note), a in zip(NOTES, answers, strict=True):
    p = {k: a[k]["probabilities"]["yes"] for k in qs}
    pred = KEY[max(p, key=p.get)]
    ok = pred == truth
    right += ok
    print(f"{truth:12} {style:9} {p['read_upstream']:6.2f} {p['read_downstream']:6.2f} "
          f"{p['read_gene_body']:6.2f}   {'OK' if ok else 'WRONG -> ' + pred}")

print(f"\n{right}/{len(NOTES)} correct")
print("Aim for clean separation: the right column high, the other two low.")
