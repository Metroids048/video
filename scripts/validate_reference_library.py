"""Validate reference library."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from avs.reference.library import validate_library


def main() -> int:
    """Validate reference library and exit with appropriate code."""
    print("验证参考知识库...")

    is_valid, errors = validate_library()

    if is_valid:
        print("✓ 参考知识库验证通过")
        return 0
    else:
        print("✗ 参考知识库验证失败：")
        for error in errors:
            print(f"  - {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
