"""
utils.py — Shared utility functions
"""

import time
import requests
from typing import Callable


def poll_until_complete(
    check_status_fn: Callable[[], dict],
    max_attempts: int = 60,
    interval: int = 15,
    success_states: list = None,
    failure_states: list = None
) -> dict:
    """Poll a status endpoint until completion or timeout"""
    if success_states is None:
        success_states = ['completed', 'success']
    if failure_states is None:
        failure_states = ['failed', 'error']

    for attempt in range(max_attempts):
        result = check_status_fn()
        status = result.get('status', '').lower()

        if status in success_states:
            print(f"Completed after {attempt + 1} checks")
            return result

        if status in failure_states:
            error_msg = result.get('error', 'Unknown error')
            raise RuntimeError(f"Generation failed: {error_msg}")

        print(f"Status: {status} (check {attempt + 1}/{max_attempts})")
        time.sleep(interval)

    raise TimeoutError(f"Polling timeout after {max_attempts * interval} seconds")


def download_file(url: str, save_path: str) -> str:
    """Download a file from a URL to local path"""
    print(f"Downloading from {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Saved to {save_path}")
    return save_path
