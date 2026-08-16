from __future__ import annotations

import sys
from pathlib import Path

from avs.models.episode import EpisodeModel
from avs.render import render_rough_cut
from avs.timeline.models import Timeline


def main() -> int:
    ep = Path(sys.argv[1]).resolve()
    model = EpisodeModel.load(ep / "episode.json")
    timeline = Timeline.load(ep / "work" / "timeline.json")
    result = render_rough_cut(ep, timeline, force=True)
    print(result)
    model.save(ep / "episode.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
