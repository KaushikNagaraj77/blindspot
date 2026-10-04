"""Turn GenBank files into loci (one per annotated CDS).

Falls back to synthetic loci when no genomes are downloaded, so the
simulator and tests work offline.
"""

from dataclasses import asdict, dataclass

import numpy as np
from Bio import SeqIO

from act.config import FLANK_BP, GENOMES_DIR

HIGH_VALUE_TERMS = ("reverse transcriptase", "integrase", "recombinase", "nuclease", "endonuclease")

# The NCBI query returns a few bacterial chromosomes carrying prophages. They
# are 50x larger than a phage and would dominate the search space, so skip them.
MAX_GENES_PER_PHAGE = 1000


@dataclass
class Locus:
    locus_id: str
    genome_id: str
    gene: str
    product: str
    start: int
    end: int
    strand: int
    high_value: bool
    upstream: str = ""  # flanking sequence, for the repeat finder; never sent to agents
    downstream: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("upstream")
        d.pop("downstream")
        return d


def load_loci(max_loci: int | None = None, with_flanks: bool = False) -> list[Locus]:
    """Parse downloaded genomes into loci. `with_flanks` also keeps FLANK_BP of
    sequence either side of each gene, which the repeat finder needs."""
    files = sorted(GENOMES_DIR.glob("*.gb"))
    if not files:
        return synthetic_loci(max_loci or 2000)

    loci: list[Locus] = []
    for f in files:
        for rec in SeqIO.parse(f, "genbank"):
            if sum(x.type == "CDS" for x in rec.features) > MAX_GENES_PER_PHAGE:
                continue
            seq = str(rec.seq).upper() if with_flanks else ""
            for i, feat in enumerate(rec.features):
                if feat.type != "CDS":
                    continue
                product = feat.qualifiers.get("product", ["hypothetical protein"])[0]
                start, end = int(feat.location.start), int(feat.location.end)
                strand = int(feat.location.strand or 1)
                # "Upstream" is before the start codon, which on the minus
                # strand means the higher coordinates.
                before, after = seq[max(0, start - FLANK_BP):start], seq[end:end + FLANK_BP]
                loci.append(
                    Locus(
                        locus_id=f"{rec.id}:{i}",
                        genome_id=rec.id,
                        gene=feat.qualifiers.get("gene", feat.qualifiers.get("locus_tag", ["?"]))[0],
                        product=product,
                        start=start,
                        end=end,
                        strand=strand,
                        high_value=any(t in product.lower() for t in HIGH_VALUE_TERMS),
                        upstream=before if strand == 1 else after,
                        downstream=after if strand == 1 else before,
                    )
                )
    return loci[:max_loci] if max_loci else loci


def synthetic_loci(n: int, seed: int = 0) -> list[Locus]:
    rng = np.random.default_rng(seed)
    loci, pos = [], 0
    for i in range(n):
        length = int(rng.integers(300, 2400))
        hv = rng.random() < 0.05
        loci.append(
            Locus(
                locus_id=f"SYN:{i}",
                genome_id=f"SYN{i // 80}",
                gene=f"g{i}",
                product="reverse transcriptase" if hv else "hypothetical protein",
                start=pos,
                end=pos + length,
                strand=1 if rng.random() < 0.5 else -1,
                high_value=hv,
            )
        )
        pos += length + int(rng.integers(20, 400))
    return loci
