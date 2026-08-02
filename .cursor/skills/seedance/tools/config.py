"""
config.py — Configuration and API key management
"""

import os
from dotenv import load_dotenv
from pathlib import Path


def _find_env() -> Path:
    """
    Walk up from this file and from cwd looking for a .env in the user's
    project root. Falls back to this file's directory.
    """
    for start in (Path(__file__).resolve().parent, Path.cwd().resolve()):
        current = start
        for _ in range(8):
            candidate = current / '.env'
            if candidate.exists():
                return candidate
            if current.parent == current:
                break
            current = current.parent
    return Path(__file__).resolve().parent / '.env'


load_dotenv(_find_env())

# API Keys
KIE_AI_API_KEY = os.getenv('KIE_AI_API_KEY')

# API Endpoints
KIE_CREATE_TASK_ENDPOINT = "https://api.kie.ai/api/v1/jobs/createTask"
KIE_TASK_STATUS_ENDPOINT = "https://api.kie.ai/api/v1/jobs/recordInfo"

# Pricing (per second)
PRICING = {
    'seedance_2_0': 0.165,  # Fast 720p
}
