"""Paths and settings shared across modules."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
GENOMES_DIR = DATA / "genomes"
EVENTS_DIR = DATA / "events"
CACHE_DIR = DATA / "cache"
DB_PATH = DATA / "act.duckdb"

REGIONS = ("gene", "upstream", "downstream")
FLANK_BP = 1500  # bases on each side counted as a flank (enough for a repeat array)

AGENT_MODEL = "claude-haiku-4-5-20251001"
ESCALATION_MODEL = "claude-sonnet-5"
LABELER_MODEL = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"  # local zero-shot NLI

MAX_USD = float(os.getenv("MAX_USD", "20"))
MAX_STEPS_PER_AGENT = 30
