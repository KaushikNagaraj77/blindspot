"""Turn GenBank files into loci (one per annotated CDS).

Falls back to synthetic loci when no genomes are downloaded, so the
simulator and tests work offline.
"""

from dataclasses import asdict, dataclass

import numpy as np
from Bio import SeqIO

from act.config import GENOMES_DIR

HIGH_VALUE_TERMS = ("reverse transcriptase", "integrase", "recombinase", "nuclease", "endonuclease")


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

    def to_dict(self) -> dict:
        return asdict(self)


def load_loci(max_loci: int | None = None) -> list[Locus]:
    files = sorted(GENOMES_DIR.glob("*.gb"))
    if not files:
        return synthetic_loci(max_loci or 2000)

    loci: list[Locus] = []
    for f in files:
        for rec in SeqIO.parse(f, "genbank"):
            for i, feat in enumerate(rec.features):
                if feat.type != "CDS":
                    continue
                product = feat.qualifiers.get("product", ["hypothetical protein"])[0]
                loci.append(
                    Locus(
                        locus_id=f"{rec.id}:{i}",
                        genome_id=rec.id,
                        gene=feat.qualifiers.get("gene", feat.qualifiers.get("locus_tag", ["?"]))[0],
                        product=product,
                        start=int(feat.location.start),
                        end=int(feat.location.end),
                        strand=int(feat.location.strand or 1),
                        high_value=any(t in product.lower() for t in HIGH_VALUE_TERMS),
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
