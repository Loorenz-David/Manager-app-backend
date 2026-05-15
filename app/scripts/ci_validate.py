from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    run(["make", "lint"])
    run(["make", "format"])
    run(["make", "test"])
    run([sys.executable, "scripts/validate_bootstrap.py"])


if __name__ == "__main__":
    main()
