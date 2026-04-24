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
        print("  sweep         Run 2-sigma outlier sweep on all spans")
        print("  sync-pricing  Refresh pricing.yaml from LiteLLM upstream")
        print("  token         Manage auth tokens (--create)")
        print("  serve         Start the FastAPI server (--host, --port, --reload)")
        return

    if args[0] == "token":
        _cmd_token(args[1:])
    elif args[0] == "serve":
        _cmd_serve(args[1:])
    elif args[0] == "sweep":
        conn = get_db()
        init_db(conn)
        result = sweep(conn)
        print(
            f"[burnmap sweep] fingerprints={result.fingerprints} "
            f"flagged={result.flagged} cleared={result.cleared}"
        )
    elif args[0] == "sync-pricing":
        from burnmap.pricing import sync_pricing_yaml
        print(sync_pricing_yaml())
    else:
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        sys.exit(1)


def _cmd_token(args: list[str]) -> None:
    from burnmap.auth import generate_token, load_token
    if "--create" in args:
        token = generate_token()
        print(f"[burnmap token] generated: {token}")
    else:
        token = load_token()
        if token:
            print(f"[burnmap token] token exists (use --create to rotate)")
        else:
            print("[burnmap token] no token set. Use --create to generate one.")


def _cmd_serve(args: list[str]) -> None:
    import uvicorn  # type: ignore[import]
    host = "127.0.0.1"
    port = 7820
    reload = False
    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]; i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1]); i += 2
        elif args[i] == "--reload":
            reload = True; i += 1
        else:
            i += 1
    uvicorn.run("burnmap.app:create_app", host=host, port=port, reload=reload, factory=True)


if __name__ == "__main__":
    main()
