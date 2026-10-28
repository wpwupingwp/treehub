#!/usr/bin/env python3
"""Render a directory of Newick files in parallel with ProcessPoolExecutor.

The preserved ``newick_phylogram.py`` renderer is imported once per worker and
reused for all tasks assigned to that worker. PNG compression remains at level
6. Existing outputs are skipped unless ``--overwrite`` is given.

Example
-------
    python batch_render_pool.py trees/ png/ --jobs 8
"""

from __future__ import annotations

import argparse
import faulthandler
import os
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import freeze_support
from pathlib import Path
from typing import Sequence

from tqdm import tqdm

__version__ = "1.3.0"

# No taxa cap is applied. Deep ladder trees need a higher Python recursion limit
# for Biopython's recursive DFS helpers (get_terminals, find_clades, ladderize).
sys.setrecursionlimit(max(sys.getrecursionlimit(), 100_000))

_WORKER_RENDER = None
_WORKER_OPTIONS: dict[str, object] = {}
_WORKER_MARKER = None


def _init_worker(options: dict[str, object]) -> None:
    """One-time setup in each worker process.

    Imports Matplotlib and the renderer once, silences expected topology-only
    warnings, performs a small warm-up, then keeps the render function in a
    module global for subsequent tasks.
    """
    import newick_phylogram as renderer

    # Recursion limit is set at module import (100,000) for the whole worker.

    # Print a Python traceback if a worker dies from a fatal signal.
    faulthandler.enable()

    # Real per-file errors are still returned by _render_task.
    renderer._warn = lambda _message: None

    fig = renderer.plt.figure(figsize=(1.2, 0.8))
    fig.text(0.1, 0.5, "Warm-up", fontweight="bold")
    fig.canvas.draw()
    renderer.plt.close(fig)

    global _WORKER_RENDER, _WORKER_OPTIONS, _WORKER_MARKER
    _WORKER_RENDER = renderer.render_newick_file
    _WORKER_OPTIONS = options
    _WORKER_MARKER = open(
        Path(str(options["marker_dir"])) / f"worker_{os.getpid()}.txt",
        "w+",
        encoding="utf-8",
        buffering=1,
    )


def _render_task(task: tuple[str, str]) -> tuple[bool, str, str, str]:
    """Render one tree; return failures instead of terminating the pool."""
    input_name, output_name = task
    marker = _WORKER_MARKER
    if marker is not None:
        marker.seek(0)
        marker.write(input_name)
        marker.truncate()
        marker.flush()
    try:
        assert _WORKER_RENDER is not None
        _WORKER_RENDER(
            Path(input_name),
            Path(output_name),
            dpi=_WORKER_OPTIONS["dpi"],
            support_scale=_WORKER_OPTIONS["support_scale"],
            no_ladderize=_WORKER_OPTIONS["no_ladderize"],
            png_compress_level=6,
        )
        return True, input_name, output_name, ""
    except Exception as exc:
        return False, input_name, output_name, f"{type(exc).__name__}: {exc}"
    finally:
        if marker is not None:
            marker.seek(0)
            marker.truncate()
            marker.flush()


def _collect_inputs(input_path: Path, patterns: Sequence[str]) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(f"input path not found: {input_path}")

    files: set[Path] = set()
    for pattern in patterns:
        files.update(path for path in input_path.glob(pattern) if path.is_file())
    return sorted(files)


def _default_jobs() -> int:
    cpu = os.cpu_count() or 1
    return max(1, min(16, cpu - 1 if cpu > 1 else 1))


def _read_worker_markers(marker_dir: Path) -> list[str]:
    active: list[str] = []
    for marker_file in marker_dir.glob("worker_*.txt"):
        try:
            text = marker_file.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            active.append(text)
    return active


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="batch_render_pool.py",
        description=(
            "Render Newick files to PNG with ProcessPoolExecutor. Existing "
            "PNGs are skipped by default."
        ),
    )
    parser.add_argument("input", type=Path, help="input directory or single Newick file")
    parser.add_argument("output_dir", type=Path, help="output directory")
    parser.add_argument(
        "--pattern",
        default="*.nwk",
        help="comma-separated glob pattern(s), e.g. '*.nwk,*.tree' (default: *.nwk)",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        "--workers",
        dest="jobs",
        type=int,
        default=None,
        help="worker processes (default: min(16, CPU count - 1))",
    )
    parser.add_argument(
        "--dpi", type=int, default=200, help="PNG resolution, at least 200 (default: 200)"
    )
    parser.add_argument(
        "--support-scale",
        choices=("auto", "fraction", "percent"),
        default="auto",
        help="interpret supports as 0-1 fractions or 0-100 percentages",
    )
    parser.add_argument(
        "--no-ladderize",
        action="store_true",
        help="keep the child order produced by rerooting",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="re-render files whose PNG already exists (default: skip existing)",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    freeze_support()
    args = _build_parser().parse_args(argv)

    if args.dpi < 200 or args.dpi > 1200:
        print("error: --dpi must be between 200 and 1200", file=sys.stderr)
        return 2
    jobs = args.jobs if args.jobs is not None else _default_jobs()
    if jobs < 1:
        print("error: --jobs must be >= 1", file=sys.stderr)
        return 2

    patterns = [part.strip() for part in args.pattern.split(",") if part.strip()]
    if not patterns:
        print("error: --pattern must not be empty", file=sys.stderr)
        return 2

    try:
        files = _collect_inputs(args.input, patterns)
    except (FileNotFoundError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not files:
        print(f"error: no input files matched {patterns!r} under {args.input}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # One directory listing is much faster than 100k+ Path.exists() calls on
    # Windows. With --overwrite we skip the listing entirely.
    existing_names: set[str] = set()
    if not args.overwrite:
        try:
            existing_names = {name.casefold() for name in os.listdir(args.output_dir)}
        except OSError as exc:
            print(f"error: cannot list output directory: {exc}", file=sys.stderr)
            return 2

    tasks: list[tuple[str, str]] = []
    skipped = 0
    empty = 0
    empty_examples: list[str] = []
    outputs_seen: set[Path] = set()
    for input_file in files:
        output_file = args.output_dir / input_file.with_suffix(".png").name
        if output_file in outputs_seen:
            print(f"error: two inputs map to the same output: {output_file}", file=sys.stderr)
            return 2
        outputs_seen.add(output_file)
        if not args.overwrite and output_file.name.casefold() in existing_names:
            skipped += 1
            continue
        tasks.append((str(input_file), str(output_file)))

    if not tasks:
        print(
            f"nothing to do: {len(files)} inputs, {skipped} already exist"
        )
        return 0

    marker_dir = Path(
        tempfile.mkdtemp(prefix=".batch_markers_", dir=str(args.output_dir))
    )
    options = {
        "dpi": args.dpi,
        "support_scale": args.support_scale,
        "no_ladderize": args.no_ladderize,
        "marker_dir": str(marker_dir),
    }

    started = time.monotonic()
    done = 0
    rendered = 0
    failed = 0
    failures: list[tuple[str, str, str]] = []
    pool_error: str | None = None

    try:
        with tqdm(total=len(tasks), desc="Rendering", unit="img") as bar:
            with ProcessPoolExecutor(
                max_workers=jobs,
                initializer=_init_worker,
                initargs=(options,),
            ) as pool:
                for ok, input_name, output_name, error in pool.map(
                    _render_task, tasks, chunksize=8
                ):
                    done += 1
                    bar.update(1)
                    if ok:
                        rendered += 1
                    else:
                        if "no trees found" in error:
                            empty += 1
                            if len(empty_examples) < 20:
                                empty_examples.append(input_name)
                        else:
                            failed += 1
                            if len(failures) < 20:
                                failures.append((input_name, output_name, error))
                            bar.set_postfix(failed=failed, refresh=False)
    except KeyboardInterrupt:
        print("\ninterrupted; existing PNGs can be skipped on the next run", file=sys.stderr)
        return 130
    except BaseException as exc:
        # Keep the useful partial summary even when a worker dies abruptly.
        pool_error = f"{type(exc).__name__}: {exc}"

    elapsed = time.monotonic() - started
    rate = done / elapsed if elapsed > 0 else 0.0
    print(
        f"done: rendered={rendered}, failed={failed}, empty={empty}, "
        f"skipped={skipped}, elapsed={elapsed:.2f}s, {rate:.2f} img/s, "
        f"workers={jobs}"
    )
    if failures:
        print("\nfailures (first 20):", file=sys.stderr)
        for input_name, output_name, error in failures:
            print(f"  {input_name} -> {output_name}: {error}", file=sys.stderr)
    if empty_examples:
        print("\nempty/no-tree inputs (first 20):", file=sys.stderr)
        for input_name in empty_examples:
            print(f"  {input_name}", file=sys.stderr)
    if pool_error:
        print(f"\nerror: worker pool failed: {pool_error}", file=sys.stderr)
        active_inputs = _read_worker_markers(marker_dir)
        if active_inputs:
            print("\nlast in-flight inputs:", file=sys.stderr)
            for input_name in active_inputs:
                print(f"  {input_name}", file=sys.stderr)
        shutil.rmtree(marker_dir, ignore_errors=True)
        if isinstance(pool_error, str) and "BrokenProcessPool" in pool_error:
            print(
                "A worker process was killed by the OS, ran out of memory, or "
                "crashed in native code. Completed PNGs are kept. Retry with "
                "fewer --jobs (e.g. 4) or on a smaller input directory.",
                file=sys.stderr,
            )
        return 1

    shutil.rmtree(marker_dir, ignore_errors=True)
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
