"""
video_gen.py — Seedance 2.0 video generation via Kie.ai
"""

import json
import requests
from typing import Optional
from .config import KIE_AI_API_KEY, KIE_CREATE_TASK_ENDPOINT, KIE_TASK_STATUS_ENDPOINT, PRICING
from .utils import poll_until_complete


def generate_video(
    prompt: str,
    duration: int = 15,
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    generate_audio: bool = True,
    start_frame_url: Optional[str] = None,
    reference_image_urls: Optional[list] = None
) -> str:
    """
    Generate a video using Seedance 2.0

    Args:
        prompt: Text description for the video (3-1536 characters)
        duration: Video duration in seconds (4-15)
        aspect_ratio: 1:1, 4:3, 3:4, 16:9, 9:16, 21:9
        resolution: 480p or 720p
        generate_audio: Whether to generate audio
        start_frame_url: Optional first frame image URL (mutually exclusive with reference_image_urls)
        reference_image_urls: Optional list of reference image URLs (mutually exclusive with start_frame_url)

    Returns:
        URL of generated video
    """
    if start_frame_url and reference_image_urls:
        raise ValueError(
            "start_frame_url and reference_image_urls are mutually exclusive."
        )

    print(f"Generating video with Seedance 2.0...")
    print(f"   Duration: {duration}s | Resolution: {resolution} | Aspect: {aspect_ratio}")
    print(f"   Prompt: {prompt[:80]}...")

    payload = {
        "model": "bytedance/seedance-2",
        "input": {
            "prompt": prompt,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "generate_audio": generate_audio,
            "web_search": False,
            "nsfw_checker": False
        }
    }

    if start_frame_url:
        payload["input"]["first_frame_url"] = start_frame_url

    if reference_image_urls:
        payload["input"]["reference_image_urls"] = reference_image_urls

    headers = {
        "Authorization": f"Bearer {KIE_AI_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(KIE_CREATE_TASK_ENDPOINT, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()

    if data.get('code') != 200:
        raise RuntimeError(f"Kie.ai error: {data.get('msg', 'Unknown error')}")

    task_id = data['data']['taskId']
    print(f"   Task ID: {task_id}")

    def check_status():
        resp = requests.get(
            KIE_TASK_STATUS_ENDPOINT,
            params={"taskId": task_id},
            headers=headers
        )
        resp.raise_for_status()
        result = resp.json()

        state = result.get('data', {}).get('state', '')
        status_map = {
            'waiting': 'pending',
            'queuing': 'pending',
            'generating': 'pending',
            'success': 'completed',
            'fail': 'failed'
        }
        return {
            'status': status_map.get(state, state),
            'data': result.get('data', {})
        }

    result = poll_until_complete(
        check_status,
        max_attempts=60,
        interval=15,
        success_states=['completed'],
        failure_states=['failed']
    )

    result_json = result.get('data', {}).get('resultJson', '{}')
    if isinstance(result_json, str):
        result_json = json.loads(result_json)

    result_urls = result_json.get('resultUrls', [])
    if not result_urls:
        raise ValueError("No video URL in Kie.ai response")

    video_url = result_urls[0]
    print(f"Video generated: {video_url}")
    return video_url


def calculate_cost(duration: int = 15, quantity: int = 1) -> float:
    """Calculate cost for Seedance 2.0 video generation"""
    return PRICING['seedance_2_0'] * duration * quantity
