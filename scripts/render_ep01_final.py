from __future__ import annotations

import json
import sys
from pathlib import Path

from avs.active import active_final_render
from avs.models.episode import EpisodeModel


def main() -> int:
    ep = Path(sys.argv[1]).resolve()
    model = EpisodeModel.load(ep / "episode.json")
    result = active_final_render(ep, model, force=True)
    print(json.dumps({key: str(value) for key, value in result.items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
