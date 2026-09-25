"""Download annotated phage genomes from NCBI (RefSeq) as GenBank files.

Usage: python -m act.genomes.fetch --n 60
"""

import argparse
import os
import time

from Bio import Entrez

from act.config import GENOMES_DIR

QUERY = 'Caudoviricetes[Organism] AND "complete genome"[Title] AND refseq[filter]'


def fetch(n: int) -> list[str]:
    email = os.getenv("NCBI_EMAIL")
    if not email:
        raise SystemExit("Set NCBI_EMAIL in .env (NCBI requires a contact email).")
    Entrez.email = email
    GENOMES_DIR.mkdir(parents=True, exist_ok=True)

    with Entrez.esearch(db="nuccore", term=QUERY, retmax=n) as h:
        ids = Entrez.read(h)["IdList"]

    saved = []
    for uid in ids:
        out = GENOMES_DIR / f"{uid}.gb"
        if out.exists():
            saved.append(uid)
            continue
        with Entrez.efetch(db="nuccore", id=uid, rettype="gbwithparts", retmode="text") as h:
            out.write_text(h.read())
        saved.append(uid)
        time.sleep(0.4)  # stay under NCBI's 3 requests/sec limit
    print(f"{len(saved)} genomes in {GENOMES_DIR}")
    return saved


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    fetch(ap.parse_args().n)
