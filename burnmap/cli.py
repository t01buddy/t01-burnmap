"""CLI entry point for t01-burnmap."""
from __future__ import annotations

import sys

from burnmap.db.schema import get_db, init_db
from burnmap.outliers import sweep


def main() -> None:
    """Dispatch CLI commands."""
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: burnmap <command>")
        print("Commands:")
        print("  sweep   Run 2-sigma outlier sweep on all spans")
        return

    if args[0] == "sweep":
        conn = get_db()
        init_db(conn)
        result = sweep(conn)
        print(
            f"[burnmap sweep] fingerprints={result.fingerprints} "
            f"flagged={result.flagged} cleared={result.cleared}"
        )
    else:
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
