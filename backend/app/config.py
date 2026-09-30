import os
from dotenv import load_dotenv

load_dotenv()

RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")

# Platform (per-server) routing values -> continent routing values
# used by Account-V5 / Match-V5 endpoints.
PLATFORM_TO_REGION = {
    "na1": "americas",
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",
    "oc1": "americas",
    "kr": "asia",
    "jp1": "asia",
    "euw1": "europe",
    "eun1": "europe",
    "tr1": "europe",
    "ru": "europe",
}

DEFAULT_PLATFORM = "na1"
MATCH_COUNT = 50  # how many recent matches to analyze
