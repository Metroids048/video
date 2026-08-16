from __future__ import annotations

import sys
from pathlib import Path

from avs.timeline.csv_export import export_csv
from avs.timeline.models import Timeline


def main() -> int:
    ep = Path(sys.argv[1]).resolve()
    export_csv(Timeline.load(ep / "work" / "timeline.json"), ep / "work" / "timeline.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
