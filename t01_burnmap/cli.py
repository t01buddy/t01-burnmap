"""CLI entry point."""
import typer
import uvicorn

app = typer.Typer(help="t01-burnmap — token usage dashboard")


@app.command()
def serve(
    host: str = "0.0.0.0",
    port: int = 7820,
    reload: bool = False,
) -> None:
    """Start the burnmap API server."""
    uvicorn.run("t01_burnmap.server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
