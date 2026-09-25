"""Free-text note templates that agents 'write'.

Explicit notes name the region; implicit notes only hint at it. The
labeler has to recover the region from the note, and the simulator knows
the truth, so we can score it exactly.
"""

EXPLICIT = {
    "gene": [
        "Read the gene body of {gene} ({product}); domain looks typical.",
        "Inspected coding sequence of {gene}. Nothing unusual in the {product} domains.",
    ],
    "upstream": [
        "Checked the upstream flank of {gene}, ~500 bp before the start.",
        "Read the region upstream of {gene} ({product}) for context.",
    ],
    "downstream": [
        "Looked at the downstream flank after {gene} ends.",
        "Read ~500 bp downstream of {gene} to check neighbours.",
    ],
}

IMPLICIT = {
    "gene": [
        "Went through {gene} end to end; the catalytic motifs are intact.",
        "{product} in {gene}: residues line up with known family members.",
    ],
    "upstream": [
        "Looked just before the start codon of {gene}; promoter-like stretch there.",
        "Scanned what precedes {gene} on its strand for anything odd.",
    ],
    "downstream": [
        "Checked what follows the stop codon of {gene}.",
        "Glanced past the end of {gene} toward the next ORF.",
    ],
}

FOUND = " Striking tandem repeat array here, CRISPR-like?!"
