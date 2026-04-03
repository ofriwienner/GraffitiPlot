"""
Compare rendering performance: vanilla matplotlib vs graffiti-plot (patched matplotlib).

Uses isolated subprocess workers so each run has a clean import path (graffiti_plot
monkey-patches matplotlib at import time).

Run the full benchmark table (including >40M points) manually:

    GRAFFITI_BENCH_LARGE=1 python tests/test_performance_mpl_vs_graffiti.py

Or with pytest (smoke sizes only by default):

    pytest tests/test_performance_mpl_vs_graffiti.py

Large sizes (~45M points ≈ 720 MiB per float64 array ×2 for x,y, plus overhead) require
GRAFFITI_BENCH_LARGE=1 and sufficient RAM.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Sizes: include one case strictly above 40M points.
BENCHMARK_SIZES_DEFAULT = (
    100_000,
    1_000_000,
    5_000_000,
    10_000_000,
    45_000_000,  # explicit > 40M
)

SMOKE_SIZES = (10_000, 100_000)

LARGE_THRESHOLD = 10_000_000


def _project_src() -> Path:
    return Path(__file__).resolve().parent.parent / "src"


def _run_worker(mode: str, n: int) -> dict:
    """Run this file as a worker subprocess; returns timing JSON dict."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_project_src()) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "worker", mode, str(n)],
        capture_output=True,
        text=True,
        timeout=7200,
        env=env,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"worker failed mode={mode} n={n} rc={proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    line = proc.stdout.strip().splitlines()[-1]
    return json.loads(line)


def _print_table(rows: list[dict]) -> None:
    headers = ("n", "mode", "data_s", "plot_s", "draw_s", "total_s")
    w = [max(len(h), *(len(str(r.get(h, ""))) for r in rows)) for h in headers]
    head = " | ".join(h.ljust(w[i]) for i, h in enumerate(headers))
    print(head)
    print("-+-".join("-" * w[i] for i in range(len(headers))))
    for r in rows:
        print(" | ".join(str(r.get(h, "")).ljust(w[i]) for i, h in enumerate(headers)))


def benchmark_sizes() -> tuple[int, ...]:
    if os.environ.get("GRAFFITI_BENCH_LARGE"):
        return BENCHMARK_SIZES_DEFAULT
    return tuple(s for s in BENCHMARK_SIZES_DEFAULT if s < LARGE_THRESHOLD)


def main() -> None:
    rows: list[dict] = []
    for n in benchmark_sizes():
        for mode in ("matplotlib", "graffiti"):
            print(f"Running {mode} n={n:,} ...", file=sys.stderr, flush=True)
            rows.append(_run_worker(mode, n))
    _print_table(rows)


def worker_main(mode: str, n_str: str) -> None:
    import gc
    import time

    import matplotlib

    matplotlib.use("Agg", force=True)

    n = int(n_str)
    t0 = time.perf_counter()
    import numpy as np

    x = np.linspace(0.0, 1.0, n, dtype=np.float64)
    y = np.sin(x * (2.0 * np.pi))
    t1 = time.perf_counter()

    if mode == "graffiti":
        import graffiti_plot  # noqa: F401 — patches matplotlib

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x, y, lw=0.5, rasterized=True)
    ax.set_title(f"{mode}  n={n:,}")
    t2 = time.perf_counter()

    fig.canvas.draw()
    t3 = time.perf_counter()

    plt.close(fig)
    gc.collect()

    result = {
        "n": n,
        "mode": mode,
        "data_s": round(t1 - t0, 6),
        "plot_s": round(t2 - t1, 6),
        "draw_s": round(t3 - t2, 6),
        "total_s": round(t3 - t0, 6),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "worker" and len(sys.argv) >= 4:
        worker_main(sys.argv[2], sys.argv[3])
    else:
        main()


@pytest.mark.parametrize("n", SMOKE_SIZES)
@pytest.mark.parametrize("mode", ("matplotlib", "graffiti"))
def test_worker_smoke(mode: str, n: int) -> None:
    """Fast subprocess checks that both code paths complete."""
    out = _run_worker(mode, n)
    assert out["n"] == n
    assert out["mode"] == mode
    assert out["total_s"] > 0


@pytest.mark.skipif(
    not os.environ.get("GRAFFITI_BENCH_LARGE"),
    reason="Set GRAFFITI_BENCH_LARGE=1 to run multi-million-point benchmarks (high RAM/time).",
)
@pytest.mark.parametrize(
    "n",
    (10_000_000, 45_000_000),
    ids=("10M", "45M_gt_40M"),
)
@pytest.mark.parametrize("mode", ("matplotlib", "graffiti"))
def test_worker_large_points(mode: str, n: int) -> None:
    """Optional: includes 45M points (>40M) for direct comparison."""
    out = _run_worker(mode, n)
    assert out["n"] == n
    assert out["mode"] == mode
