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
        print("  content       Manage prompt content (wipe, mode)")
        print("  statusline    Emit one-line summary for Claude Code statusline API")
        return

    if args[0] == "token":
        _cmd_token(args[1:])
    elif args[0] == "serve":
        _cmd_serve(args[1:])
    elif args[0] == "content":
        _cmd_content(args[1:])
    elif args[0] == "statusline":
        _cmd_statusline()
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


def _cmd_content(args: list[str]) -> None:
    if not args or args[0] in ("-h", "--help"):
        print("Usage: burnmap content <subcommand>")
        print("Subcommands:")
        print("  wipe         Delete all stored prompt_content rows")
        print("  mode <mode>  Set content mode (preview|full)")
        return
    if args[0] == "wipe":
        from burnmap.db.schema import get_content_db, init_content_db
        from burnmap.fingerprint import wipe_content
        cconn = get_content_db()
        init_content_db(cconn)
        deleted = wipe_content(cconn)
        cconn.close()
        print(f"[burnmap content wipe] deleted={deleted}")
    elif args[0] == "mode":
        if len(args) < 2:
            print("Usage: burnmap content mode <mode>", file=sys.stderr)
            sys.exit(1)
        from burnmap.api.content import set_content_mode
        try:
            set_content_mode(args[1])
            print(f"[burnmap content mode] set to {args[1]!r}")
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unknown content subcommand: {args[0]}", file=sys.stderr)
        sys.exit(1)


def _cmd_statusline() -> None:
    """Emit a one-line burnmap summary for Claude Code's statusline API.

    Output format: "burnmap | N sessions · $X.XXXX today · A live"
    Non-blocking: returns immediately with stale data on DB error.
    """
    import time
    try:
        conn = get_db()
        init_db(conn)
        now_ms = int(time.time() * 1000)
        day_ms = 24 * 60 * 60 * 1000
        hour_ms = 60 * 60 * 1000

        # Sessions in last 24h
        row = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE started_at >= ?",
            (now_ms - day_ms,),
        ).fetchone()
        session_count = row[0] if row else 0

        # Total cost from spans in last 24h
        row = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM spans WHERE started_at >= ?",
            (now_ms - day_ms,),
        ).fetchone()
        cost_today = row[0] if row else 0.0

        # Live agents: sessions started in last hour with no ended_at
        row = conn.execute(
            "SELECT COUNT(DISTINCT agent) FROM sessions "
            "WHERE started_at >= ? AND (ended_at = 0 OR ended_at IS NULL)",
            (now_ms - hour_ms,),
        ).fetchone()
        live_agents = row[0] if row else 0

        conn.close()
        print(f"burnmap | {session_count} sessions · ${cost_today:.4f} today · {live_agents} live")
    except Exception:
        print("burnmap | unavailable")


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
