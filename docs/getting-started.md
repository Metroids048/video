# Getting Started — Creator OS V2

## 1. Check the environment

Run:

```bash
python -m avs doctor
python scripts/validate_creator_os_v2.py
```

The validator checks the V2 configuration/contracts and verifies that deleted quant/EP01 residue has not been reintroduced.

## 2. Start with source material, not a giant prompt

For each new Episode, provide:
- a real problem/project node;
- at least one factual source;
- screen recording/screenshots when available;
- optional rough voice;
- 1–3 useful reference links/videos;
- privacy/redaction boundary.

The system is responsible for deciding whether VIDEO, CAROUSEL or TEXT is strongest.

## 3. Reference links

Douyin links are accepted directly. The system may resolve/cache publicly accessible media and analyze the local copy. If acquisition is unavailable, it must preserve the URL and mark the evidence as page-only rather than pretend the full video was reviewed.

## 4. Do not revive historical EP01 builders

The V2 branch intentionally removed one-off `build_ep01_v*`, `final_final_lock` and historical completion-report paths. Reusable implementation belongs in the core engine/config/Skills; Episode-specific artifacts belong inside the Episode.

## 5. Completion

`READY_TO_PUBLISH` means the content can be uploaded without mandatory manual re-editing. Anything short of that is `BLOCKED`, `REPAIR`, `WAITING_FOR_RESOURCE` or `FAILED`.
