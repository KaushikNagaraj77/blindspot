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
FLANK_BP = 500  # bases on each side counted as a flank

AGENT_MODEL = "claude-haiku-4-5-20251001"
ESCALATION_MODEL = "claude-sonnet-5"
JEV_MODEL = "jev-1.13.0"
JEV_URL = "https://api.typesafe.ai/v1/systemone"

MAX_USD = float(os.getenv("MAX_USD", "20"))
MAX_STEPS_PER_AGENT = 30
