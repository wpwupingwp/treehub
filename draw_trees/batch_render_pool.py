#!/usr/bin/env python3
"""Render many Newick files in parallel with the preserved renderer.

This is the pool-only batch entry recommended for 200k-scale jobs.  It imports
the untouched ``newick_phylogram.py`` once per worker, so no separate fast
renderer needs to be maintained.  PNG compression stays at level 6.

Typical use::

    python batch_render_pool.py trees/ png/ --jobs 8 --recursive

Existing PNGs are skipped by default, which makes the job resumable after a
crash.  Use ``--overwrite`` to force a full re-render.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import freeze_support
from pathlib import Path
from typing import Any, Sequence

__version__ = "1.0.0"

_WORKER_RENDER = None
_WORKER_OPTIONS: dict[str, Any] = {}


def _init_worker(options: dict[str, Any]) -> None:
    """One-time setup inside each Windows/Linux worker process."""
    # Avoid BLAS/OpenMP thread oversubscription when many workers are used.
    for key in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[key] = "1"
    os.environ["MPLBACKEND"] = "Agg"

    import newick_phylogram as renderer

    # Topology-only warnings would produce one line per input in a 200k batch;
    # real per-file errors are still returned to the parent by _render_task.
    renderer._warn = lambda _message: None

    # One-time text/backend warm-up (the renderer imports pyplot already).
    fig = renderer.plt.figure(figsize=(1.2, 0.8))
    fig.text(0.1, 0.5, "Warm-up", fontweight="bold")
    fig.canvas.draw()
    renderer.plt.close(fig)

    global _WORKER_RENDER, _WORKER_OPTIONS
    _WORKER_RENDER = renderer.render_newick_file
    _WORKER_OPTIONS = options


def _render_task(task: tuple[str, str]) -> tuple[bool, str, str, str]:
    """Worker entry point. Never raise: errors are returned to the parent."""
    input_name, output_name = task
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
    except Exception as exc:  # keep the pool alive after one bad tree
        return False, input_name, output_name, f"{type(exc).__name__}: {exc}"


def _collect_inputs(
    input_path: Path,
    patterns: Sequence[str],
    recursive: bool,
) -> tuple[list[Path], Path | None]:
    if input_path.is_file():
        return [input_path], None
    if not input_path.is_dir():
        raise FileNotFoundError(f"input path not found: {input_path}")

    files: set[Path] = set()
    for pattern in patterns:
        iterator = input_path.rglob(pattern) if recursive else input_path.glob(pattern)
        files.update(path for path in iterator if path.is_file())
    return sorted(files), input_path


def _output_path_for(
    input_file: Path,
    input_root: Path | None,
    output_root: Path,
    recursive: bool,
) -> Path:
    if input_root is None:
        return output_root / input_file.with_suffix(".png").name
    if recursive:
        relative = input_file.relative_to(input_root)
        return output_root / relative.with_suffix(".png")
    return output_root / input_file.with_suffix(".png").name


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="batch_render_pool.py",
        description=(
            "Render a directory/file of Newick trees to PNG in parallel. "
            "Uses newick_phylogram.py; existing outputs are skipped by "
            "default so interrupted runs can resume."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="input directory or single .nwk file")
    parser.add_argument("output_dir", type=Path, help="output directory for PNG files")
    parser.add_argument(
        "--pattern",
        default="*.nwk",
        help="comma-separated glob pattern(s), e.g. '*.nwk,*.tree' (default: *.nwk)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="recurse into subdirectories; relative subpaths are preserved in output",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        "--workers",
        dest="jobs",
        type=int,
        default=None,
        help="worker processes (default: min(16, cpu_count-1))",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=8,
        help="tasks per ProcessPoolExecutor chunk (default: 8)",
    )
    parser.add_argument(
        "--start-method",
        choices=("spawn", "fork", "forkserver"),
        default=None,
        help=(
            "multiprocessing start method; default is platform default. "
            "Windows always uses spawn."
        ),
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="PNG resolution, at least 200 (default: 200)",
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
        "--limit",
        type=int,
        default=0,
        help="render only the first N inputs; 0 means all (default: 0)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="re-render files whose PNG already exists (default: skip existing)",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="suppress periodic progress lines",
    )
    parser.add_argument(
        "--progress-interval",
        type=float,
        default=5.0,
        help="seconds between progress lines (default: 5)",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def _default_jobs() -> int:
    cpu = os.cpu_count() or 1
    return max(1, min(16, cpu - 1 if cpu > 1 else 1))


def main(argv: Sequence[str] | None = None) -> int:
    freeze_support()  # required by frozen/spawn Windows executables
    args = _build_parser().parse_args(argv)

    if args.dpi < 200 or args.dpi > 1200:
        print("error: --dpi must be between 200 and 1200", file=sys.stderr)
        return 2
    jobs = args.jobs if args.jobs is not None else _default_jobs()
    if jobs < 1:
        print("error: --jobs must be >= 1", file=sys.stderr)
        return 2
    if args.chunksize < 1:
        print("error: --chunksize must be >= 1", file=sys.stderr)
        return 2
    if args.limit < 0:
        print("error: --limit must be >= 0", file=sys.stderr)
        return 2

    patterns = [part.strip() for part in args.pattern.split(",") if part.strip()]
    if not patterns:
        print("error: --pattern must not be empty", file=sys.stderr)
        return 2

    try:
        files, input_root = _collect_inputs(args.input, patterns, args.recursive)
    except (FileNotFoundError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.limit:
        files = files[: args.limit]
    if not files:
        print(f"error: no input files matched {patterns!r} under {args.input}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)

    tasks: list[tuple[str, str]] = []
    skipped = 0
    outputs_seen: set[Path] = set()
    for input_file in files:
        output_file = _output_path_for(input_file, input_root, args.output_dir, args.recursive)
        if output_file in outputs_seen:
            print(f"error: two inputs map to the same output: {output_file}", file=sys.stderr)
            return 2
        outputs_seen.add(output_file)
        if output_file.exists() and not args.overwrite:
            skipped += 1
            continue
        tasks.append((str(input_file), str(output_file)))

    total = len(files)
    if not tasks:
        print(f"nothing to do: {total} inputs, {skipped} already exist")
        return 0

    options = {
        "dpi": args.dpi,
        "support_scale": args.support_scale,
        "no_ladderize": args.no_ladderize,
    }

    mp_context = None
    if args.start_method:
        try:
            mp_context = mp.get_context(args.start_method)
        except ValueError as exc:
            print(f"error: start method {args.start_method!r} is unavailable: {exc}", file=sys.stderr)
            return 2

    started = time.monotonic()
    done = 0
    failed = 0
    failures: list[tuple[str, str, str]] = []
    last_progress = started
    next_hint = min(1000, len(tasks))

    print(
        f"rendering {len(tasks)} PNGs with {jobs} process(es), "
        f"{skipped} skipped, dpi={args.dpi}, zlib=6",
        flush=True,
    )

    try:
        with ProcessPoolExecutor(
            max_workers=jobs,
            initializer=_init_worker,
            initargs=(options,),
            mp_context=mp_context,
        ) as pool:
            for ok, input_name, output_name, error in pool.map(
                _render_task, tasks, chunksize=args.chunksize
            ):
                done += 1
                if not ok:
                    failed += 1
                    if len(failures) < 20:
                        failures.append((input_name, output_name, error))
                now = time.monotonic()
                if not args.no_progress and now - last_progress >= args.progress_interval:
                    elapsed = now - started
                    rate = done / elapsed if elapsed > 0 else 0.0
                    remaining = len(tasks) - done
                    eta = remaining / rate if rate > 0 else 0.0
                    print(
                        f"  {done}/{len(tasks)} "
                        f"({100.0 * done / len(tasks):5.1f}%)  "
                        f"{rate:6.2f} img/s  ETA {eta/60:6.1f} min  "
                        f"failed={failed}",
                        flush=True,
                    )
                    last_progress = now
                elif not args.no_progress and done >= next_hint and len(tasks) > 1000:
                    # Keep some feedback on very fast runs between timed lines.
                    elapsed = now - started
                    rate = done / elapsed if elapsed > 0 else 0.0
                    print(f"  {done}/{len(tasks)}  {rate:6.2f} img/s", flush=True)
                    next_hint = min(len(tasks), next_hint * 2)
    except KeyboardInterrupt:
        print("\ninterrupted; already-written PNGs can be resumed with the same command", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"error: worker pool failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    elapsed = time.monotonic() - started
    rate = done / elapsed if elapsed > 0 else 0.0
    print(
        f"done: rendered={done - failed}, failed={failed}, skipped={skipped}, "
        f"elapsed={elapsed:.2f}s, {rate:.2f} img/s, workers={jobs}"
    )
    if failures:
        print("\nfailures (first 20):", file=sys.stderr)
        for input_name, output_name, error in failures:
            print(f"  {input_name} -> {output_name}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
