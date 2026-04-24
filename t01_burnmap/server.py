"""FastAPI server stub."""
from fastapi import FastAPI

app = FastAPI(title="t01-burnmap")


@app.get("/")
def root() -> dict:
    return {"status": "ok", "service": "t01-burnmap"}
