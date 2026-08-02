---
name: seedance
description: This skill should be used when the user asks to "generate a Seedance video", "create a Seedance video with this folder", mentions "Seedance", or wants to generate video from a folder of reference images using Seedance 2.0.
version: 1.0.0
---

# Seedance 2.0 Video Generation

Generate videos from a folder of reference images using Bytedance Seedance 2.0 via Kie.ai.

## Trigger

User says something like:
- "Generate a Seedance video with [folder name]"
- "Create a Seedance video for [folder name]"
- "Seedance video from [folder name]"

## Workflow

Follow these steps exactly:

### 1. Locate the project folder

The folder lives at `references/[folder-name]/`. Confirm it exists and list the images inside.

If the folder doesn't exist or has no images, tell the user and stop.

### 2. View the reference images

Read each image so you can write an accurate video prompt based on their content.

### 3. Write a video prompt

Based on the reference images and any context the user has given, write a video prompt:

```
[Opening frame] + [Camera movement] + [Motion elements] + [Pacing] + [Duration + format]
```

Present the prompt to the user for approval before generating.

### 4. Show cost estimate and confirm

Calculate and display costs before generating. Default is 15 seconds, 720p, 16:9:

```
Cost Estimate
----------------------------------------
Seedance 2.0 (Fast 720p)  1 x $0.165/sec x 15s = $2.48
----------------------------------------
Total: $2.48

Proceed? (yes/no)
```

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.claude/skills/seedance').resolve()))
from tools.video_gen import calculate_cost
total = calculate_cost(duration=15, quantity=1)
```

Do NOT proceed until the user confirms.

### 5. Generate the video

The reference images need to be publicly accessible URLs. Since users place local files in the `references/` folder, you need to upload them first. Use a quick Python snippet to read each image and convert to a data URI or use any available upload method the user has configured.

**If the images are already URLs**, pass them directly. **If they are local files**, the user must provide public URLs or have an upload tool configured.

**IMPORTANT:** `start_frame_url` and `reference_image_urls` are **mutually exclusive** — you cannot use both. When generating from a folder of reference images, only use `reference_image_urls`.

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.claude/skills/seedance').resolve()))
from tools.video_gen import generate_video

video_url = generate_video(
    prompt="your approved prompt here",
    duration=15,
    aspect_ratio="16:9",
    resolution="720p",
    generate_audio=True,
    reference_image_urls=image_urls
)
```

**Generation takes ~4-5 minutes.** The polling loop handles this automatically.

### 6. Save the output

Download the generated video to the `output/` folder:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.claude/skills/seedance').resolve()))
from tools.utils import download_file

download_file(video_url, 'output/[folder-name]-seedance.mp4')
```

### 7. Report completion

Tell the user:
- Where the video was saved (output folder path)
- The video URL (temporary — will expire)
- Remind them to download or move the file from `output/` if they need it long-term

## Defaults

| Setting | Default | Notes |
|---|---|---|
| Resolution | 720p | Fast tier |
| Aspect ratio | 16:9 | Landscape/widescreen |
| Duration | 15 seconds | Range: 4-15s |
| Audio | Enabled | Adds to cost |
| NSFW filter | Disabled | |
| Max reference images | 9 | 2-3 recommended for best blending |

The user can override any of these by specifying in their request (e.g. "make it 9:16" or "10 seconds").
