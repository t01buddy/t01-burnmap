"""Pricing engine — effective-dated per-model token rates.

Reads from pricing.yaml (vendored at build time). Supports lookup by
model name and date, returning the rates effective on that date.
Sessions are labeled 'synthetic' (context-mode/tool runs) or 'real' (API).
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import TypedDict

try:
    import yaml as _yaml  # type: ignore
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

_PRICING_YAML = Path(__file__).parent / "pricing.yaml"

# Fallback rates when model is unknown (conservative mid-tier estimate)
_FALLBACK_RATES: "ModelRates" = {
    "input_per_1m": 3.0,
    "output_per_1m": 15.0,
    "cached_per_1m": 0.3,
}


class ModelRates(TypedDict):
    input_per_1m: float
    output_per_1m: float
    cached_per_1m: float


def _load_pricing() -> dict[str, list[dict]]:
    """Load pricing.yaml into memory. Returns empty dict on missing YAML dep."""
    if not _HAS_YAML or not _PRICING_YAML.exists():
        return {}
    with _PRICING_YAML.open() as f:
        data = _yaml.safe_load(f)
    return data.get("models", {})


_PRICING_CACHE: dict[str, list[dict]] | None = None


def _get_pricing() -> dict[str, list[dict]]:
    global _PRICING_CACHE
    if _PRICING_CACHE is None:
        _PRICING_CACHE = _load_pricing()
    return _PRICING_CACHE


def lookup_rates(model: str, date: str | datetime.date | None = None) -> ModelRates:
    """Return effective rates for *model* on *date*.

    *date* can be 'YYYY-MM-DD', a ``datetime.date``, or None (today).
    Falls back to ``_FALLBACK_RATES`` for unknown models.
    """
    if date is None:
        ref = datetime.date.today()
    elif isinstance(date, str):
        ref = datetime.date.fromisoformat(date)
    else:
        ref = date

    pricing = _get_pricing()
    entries = pricing.get(model)
    if not entries:
        return dict(_FALLBACK_RATES)  # type: ignore[return-value]

    # Pick latest entry whose effective_from <= ref
    best: dict | None = None
    for entry in sorted(entries, key=lambda e: e["effective_from"]):
        if datetime.date.fromisoformat(entry["effective_from"]) <= ref:
            best = entry
    if best is None:
        return dict(_FALLBACK_RATES)  # type: ignore[return-value]

    return {
        "input_per_1m": float(best["input_per_1m"]),
        "output_per_1m": float(best["output_per_1m"]),
        "cached_per_1m": float(best.get("cached_per_1m", 0.0)),
    }


def compute_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    date: str | datetime.date | None = None,
) -> float:
    """Compute USD cost for a single request given token counts."""
    rates = lookup_rates(model, date)
    cost = (
        input_tokens * rates["input_per_1m"] / 1_000_000
        + output_tokens * rates["output_per_1m"] / 1_000_000
        + cached_tokens * rates["cached_per_1m"] / 1_000_000
    )
    return round(cost, 8)


# Billing label constants
LABEL_SYNTHETIC = "synthetic"
LABEL_REAL = "real"

_SYNTHETIC_KINDS = {"tool", "slash", "skill"}


def billing_label(kind: str) -> str:
    """Return 'synthetic' for context-mode/tool runs, 'real' for API calls."""
    return LABEL_SYNTHETIC if kind in _SYNTHETIC_KINDS else LABEL_REAL


def sync_pricing_yaml(dest: Path | None = None) -> str:
    """Refresh pricing.yaml from the LiteLLM pricing endpoint.

    Returns a status message. Uses stdlib urllib only (no extra deps).
    On network failure, leaves existing file untouched.
    """
    import json
    import urllib.request

    target = dest or _PRICING_YAML
    url = (
        "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            raw: dict = json.loads(resp.read())
    except Exception as exc:
        return f"[sync-pricing] network error: {exc} — pricing.yaml unchanged"

    # Build effective-dated entries from the flat LiteLLM format
    today = datetime.date.today().isoformat()
    models: dict[str, list[dict]] = {}
    for name, info in raw.items():
        if not isinstance(info, dict):
            continue
        inp = info.get("input_cost_per_token")
        out = info.get("output_cost_per_token")
        if inp is None or out is None:
            continue
        cached = info.get("cache_read_input_token_cost", inp * 0.1)
        models[name] = [{
            "effective_from": today,
            "input_per_1m": round(float(inp) * 1_000_000, 4),
            "output_per_1m": round(float(out) * 1_000_000, 4),
            "cached_per_1m": round(float(cached) * 1_000_000, 4),
        }]

    if not _HAS_YAML:
        return "[sync-pricing] PyYAML not installed — cannot write pricing.yaml"

    import yaml  # type: ignore
    with target.open("w") as f:
        f.write(f"# Vendored LiteLLM pricing snapshot — effective-dated model rates.\n")
        f.write(f"# Last synced: {today}\n")
        yaml.dump({"models": models}, f, default_flow_style=False, allow_unicode=True)

    # Bust cache
    global _PRICING_CACHE
    _PRICING_CACHE = None
    return f"[sync-pricing] wrote {len(models)} models to {target}"
