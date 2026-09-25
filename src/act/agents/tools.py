"""Tools the real search agents can call. Every call is logged as ground truth.

Agents never see raw DNA: tools return compact summaries only.
"""

from act.genomes.parse import Locus

TOOL_DEFS = [
    {
        "name": "list_loci",
        "description": "List annotated genes on a page of the search space. Returns id, gene, product.",
        "input_schema": {
            "type": "object",
            "properties": {"page": {"type": "integer", "minimum": 0}},
            "required": ["page"],
        },
    },
    {
        "name": "inspect",
        "description": (
            "Inspect one region of a locus. region is 'gene' (the coding sequence), "
            "'upstream' (~500 bp before the gene) or 'downstream' (~500 bp after). "
            "Returns a compact summary, not raw sequence."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "locus_id": {"type": "string"},
                "region": {"type": "string", "enum": ["gene", "upstream", "downstream"]},
            },
            "required": ["locus_id", "region"],
        },
    },
]

PAGE_SIZE = 25


class ToolEnv:
    def __init__(self, loci: list[Locus], target_id: str):
        self.loci = loci
        self.by_id = {loc.locus_id: loc for loc in loci}
        self.target_id = target_id
        self.log: list[dict] = []  # ground truth: every region actually read

    def call(self, name: str, args: dict, ctx: dict) -> str:
        if name == "list_loci":
            page = self.loci[args["page"] * PAGE_SIZE:(args["page"] + 1) * PAGE_SIZE]
            return "\n".join(f"{loc.locus_id}\t{loc.gene}\t{loc.product}" for loc in page) or "empty"

        if name == "inspect":
            loc = self.by_id.get(args["locus_id"])
            if loc is None:
                return "error: unknown locus_id"
            region = args["region"]
            self.log.append({**ctx, "locus_id": loc.locus_id, "region": region})
            return self._summary(loc, region)

        return "error: unknown tool"

    def _summary(self, loc: Locus, region: str) -> str:
        if region == "gene":
            return f"{loc.gene}: {loc.product}, {loc.end - loc.start} bp, strand {loc.strand}."
        if region == "upstream" and loc.locus_id == self.target_id:
            return ("Upstream flank: 11 direct repeats of 36 bp separated by 30-bp spacers "
                    "(tandem repeat array); small ORF of unknown function nearby.")
        return f"{region.capitalize()} flank: no repeats; intergenic spacer and neighbouring ORF."
