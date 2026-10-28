#!/usr/bin/env python3
"""Batch-render Newick trees: parallel small trees, then serial large trees.

The first run classifies every input into:

    list_small.txt    # <= --big-threshold taxa
    list_big.txt      # >  --big-threshold taxa
    list_invalid.txt  # parse errors / no trees

and writes list_meta.json next to them. Later runs reuse those lists unless
--rebuild-lists is given, so startup does not re-parse every Newick file.

Rendering then runs in two phases:

1. small trees with a ProcessPoolExecutor (parallel);
2. big trees with a one-worker ProcessPoolExecutor (strictly serial).

The preserved ``newick_phylogram.py`` renderer is imported once per worker.
PNG compression remains at zlib level 6.

Example
-------
    python batch_render_pool.py trees/ png/ --jobs 8
"""

from __future__ import annotations

import argparse
import faulthandler
import json
import os
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import freeze_support
from pathlib import Path
from typing import Sequence

from Bio import Phylo
from tqdm import tqdm

__version__ = "2.0.0"

# Biopython's tree traversal helpers are recursive. Set this before any parse
# or traversal; workers inherit the module-level setting.
sys.setrecursionlimit(max(sys.getrecursionlimit(), 100_000))

DEFAULT_BIG_THRESHOLD = 500
MAX_FIGURE_HEIGHT_IN = 120.0
LIST_SMALL = "list_small.txt"
LIST_BIG = "list_big.txt"
LIST_INVALID = "list_invalid.txt"
LIST_META = "list_meta.json"

_WORKER_RENDER = None
_WORKER_OPTIONS: dict[str, object] = {}
_WORKER_MARKER = None


def _init_worker(options: dict[str, object]) -> None:
    """One-time setup in each worker process."""
    import newick_phylogram as renderer

    faulthandler.enable()

    # Expected topology-only warnings would be one line per tree.
    renderer._warn = lambda _message: None

    # The batch can render six-figure-pixel images for large trees; cap the
    # height so a single figure does not grow without bound.
    original_adaptive = renderer._adaptive_figure_size

    def capped_adaptive(n_tips, n_nodes, max_label_length, topology_only=False):
        width, height = original_adaptive(
            n_tips, n_nodes, max_label_length, topology_only=topology_only
        )
        return width, min(height, MAX_FIGURE_HEIGHT_IN)

    renderer._adaptive_figure_size = capped_adaptive

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


def _atomic_write_lines(path: Path, lines: Sequence[str]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line)
            handle.write("\n")
    temporary.replace(path)


def _list_paths(output_dir: Path) -> tuple[Path, Path, Path, Path]:
    return (
        output_dir / LIST_SMALL,
        output_dir / LIST_BIG,
        output_dir / LIST_INVALID,
        output_dir / LIST_META,
    )


def _load_cache(
    input_path: Path,
    output_dir: Path,
    patterns: Sequence[str],
    big_threshold: int,
) -> tuple[list[str], list[str], list[str]] | None:
    small_path, big_path, invalid_path, meta_path = _list_paths(output_dir)
    if not all(path.is_file() for path in (small_path, big_path, invalid_path, meta_path)):
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (
        meta.get("big_threshold") != big_threshold
        or meta.get("input") != str(input_path.resolve())
        or meta.get("patterns") != list(patterns)
    ):
        return None

    def read_paths(path: Path) -> list[str]:
        return [
            line.split("\t", 1)[0]
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    return read_paths(small_path), read_paths(big_path), read_paths(invalid_path)


def _classify_inputs(
    input_path: Path,
    output_dir: Path,
    patterns: Sequence[str],
    big_threshold: int,
) -> tuple[list[str], list[str], list[str]]:
    files = _collect_inputs(input_path, patterns)
    if not files:
        raise FileNotFoundError(
            f"no input files matched {list(patterns)!r} under {input_path}"
        )

    small: list[str] = []
    big: list[str] = []
    invalid: list[str] = []
    for input_file in tqdm(files, desc="Classifying", unit="tree"):
        absolute = str(input_file.resolve())
        try:
            tree = Phylo.read(str(input_file), "newick")
            n_tips = len(tree.get_terminals())
            if n_tips <= 0:
                invalid.append(f"{absolute}\tValueError: no taxa found")
            elif n_tips <= big_threshold:
                small.append(absolute)
            else:
                big.append(absolute)
        except Exception as exc:
            invalid.append(f"{absolute}\t{type(exc).__name__}: {exc}")

    small_path, big_path, invalid_path, meta_path = _list_paths(output_dir)
    _atomic_write_lines(small_path, small)
    _atomic_write_lines(big_path, big)
    _atomic_write_lines(invalid_path, invalid)
    meta = {
        "version": __version__,
        "input": str(input_path.resolve()),
        "patterns": list(patterns),
        "big_threshold": big_threshold,
        "counts": {
            "small": len(small),
            "big": len(big),
            "invalid": len(invalid),
        },
    }
    temporary_meta = meta_path.with_suffix(meta_path.suffix + ".tmp")
    temporary_meta.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    temporary_meta.replace(meta_path)
    return small, big, invalid


def _existing_output_names(output_dir: Path) -> set[str]:
    try:
        return {name.casefold() for name in os.listdir(output_dir)}
    except OSError as exc:
        raise OSError(f"cannot list output directory: {exc}") from exc


def _build_tasks(
    files: Sequence[str],
    output_dir: Path,
    existing_names: set[str],
    overwrite: bool,
    outputs_seen: set[Path],
) -> tuple[list[tuple[str, str]], int]:
    tasks: list[tuple[str, str]] = []
    skipped = 0
    for input_name in files:
        input_file = Path(input_name)
        output_file = output_dir / input_file.with_suffix(".png").name
        if output_file in outputs_seen:
            raise ValueError(f"two inputs map to the same output: {output_file}")
        outputs_seen.add(output_file)
        if not overwrite and output_file.name.casefold() in existing_names:
            skipped += 1
            continue
        tasks.append((input_name, str(output_file)))
    return tasks, skipped


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


def _default_jobs() -> int:
    cpu = os.cpu_count() or 1
    return max(1, min(16, cpu - 1 if cpu > 1 else 1))


def _run_phase(
    tasks: Sequence[tuple[str, str]],
    jobs: int,
    desc: str,
    options: dict[str, object],
    marker_dir: Path,
) -> dict[str, object]:
    if not tasks:
        return {
            "rendered": 0,
            "failed": 0,
            "empty": 0,
            "failures": [],
            "empty_examples": [],
            "pool_error": None,
        }

    rendered = 0
    failed = 0
    empty = 0
    failures: list[tuple[str, str, str]] = []
    empty_examples: list[str] = []
    pool_error: str | None = None

    try:
        with tqdm(total=len(tasks), desc=desc, unit="img") as bar:
            with ProcessPoolExecutor(
                max_workers=jobs,
                initializer=_init_worker,
                initargs=(options,),
            ) as pool:
                for ok, input_name, output_name, error in pool.map(
                    _render_task, tasks, chunksize=8 if jobs > 1 else 1
                ):
                    bar.update(1)
                    if ok:
                        rendered += 1
                    elif "no trees found" in error:
                        empty += 1
                        if len(empty_examples) < 20:
                            empty_examples.append(input_name)
                    else:
                        failed += 1
                        if len(failures) < 20:
                            failures.append((input_name, output_name, error))
                        bar.set_postfix(failed=failed, refresh=False)
    except KeyboardInterrupt:
        raise
    except BaseException as exc:
        pool_error = f"{type(exc).__name__}: {exc}"

    return {
        "rendered": rendered,
        "failed": failed,
        "empty": empty,
        "failures": failures,
        "empty_examples": empty_examples,
        "pool_error": pool_error,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="batch_render_pool.py",
        description=(
            "Render Newick files to PNG. Small trees run in parallel, large "
            "trees run serially. Input classification is cached in list files."
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
        help="parallel workers for small trees (default: min(16, CPU count - 1))",
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
        "--big-threshold",
        type=int,
        default=DEFAULT_BIG_THRESHOLD,
        help=(
            "trees with more than N taxa go to the serial big-tree phase "
            f"(default: {DEFAULT_BIG_THRESHOLD})"
        ),
    )
    parser.add_argument(
        "--no-ladderize",
        action="store_true",
        help="keep the child order produced by rerooting",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="re-render existing PNGs (default: skip them)",
    )
    parser.add_argument(
        "--rebuild-lists",
        action="store_true",
        help="rescan inputs and rebuild list_small/list_big/list_invalid",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    freeze_support()
    total_started = time.monotonic()
    args = _build_parser().parse_args(argv)

    if args.dpi < 200 or args.dpi > 1200:
        print("error: --dpi must be between 200 and 1200", file=sys.stderr)
        return 2
    jobs = args.jobs if args.jobs is not None else _default_jobs()
    if jobs < 1:
        print("error: --jobs must be >= 1", file=sys.stderr)
        return 2
    if args.big_threshold < 0:
        print("error: --big-threshold must be >= 0", file=sys.stderr)
        return 2

    patterns = [part.strip() for part in args.pattern.split(",") if part.strip()]
    if not patterns:
        print("error: --pattern must not be empty", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)

    cached = None
    if not args.rebuild_lists:
        cached = _load_cache(
            args.input, args.output_dir, patterns, args.big_threshold
        )
    if cached is not None:
        small_files, big_files, invalid = cached
        print(
            f"using cached lists: small={len(small_files)}, "
            f"big={len(big_files)}, invalid={len(invalid)}"
        )
    else:
        scan_started = time.monotonic()
        try:
            small_files, big_files, invalid = _classify_inputs(
                args.input, args.output_dir, patterns, args.big_threshold
            )
        except (FileNotFoundError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(
            f"classified {len(small_files) + len(big_files) + len(invalid)} trees "
            f"in {time.monotonic() - scan_started:.2f}s: "
            f"small={len(small_files)}, big={len(big_files)}, invalid={len(invalid)}"
        )

    if not args.overwrite:
        try:
            existing_names = _existing_output_names(args.output_dir)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    else:
        existing_names = set()

    outputs_seen: set[Path] = set()
    try:
        small_tasks, small_skipped = _build_tasks(
            small_files, args.output_dir, existing_names, args.overwrite, outputs_seen
        )
        big_tasks, big_skipped = _build_tasks(
            big_files, args.output_dir, existing_names, args.overwrite, outputs_seen
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not small_tasks and not big_tasks:
        print(
            f"nothing to do: small={len(small_files)}, big={len(big_files)}, "
            f"invalid={len(invalid)}, skipped={small_skipped + big_skipped}"
        )
        if invalid:
            print("\ninvalid inputs (first 20 from list_invalid.txt):", file=sys.stderr)
            for entry in invalid[:20]:
                print(f"  {entry}", file=sys.stderr)
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

    aggregate = {
        "rendered": 0,
        "failed": 0,
        "empty": 0,
        "failures": [],
        "empty_examples": [],
    }
    pool_error: str | None = None

    print(
        f"small trees: {len(small_tasks)} queued "
        f"({small_skipped} existing skipped), jobs={jobs}"
    )
    try:
        stats = _run_phase(small_tasks, jobs, "Small trees", options, marker_dir)
    except KeyboardInterrupt:
        print("\ninterrupted; existing PNGs can be skipped on the next run", file=sys.stderr)
        active_inputs = _read_worker_markers(marker_dir)
        if active_inputs:
            print("\nlast in-flight inputs:", file=sys.stderr)
            for input_name in active_inputs:
                print(f"  {input_name}", file=sys.stderr)
        shutil.rmtree(marker_dir, ignore_errors=True)
        return 130
    for key in ("rendered", "failed", "empty"):
        aggregate[key] += stats[key]
    aggregate["failures"].extend(stats["failures"])
    aggregate["empty_examples"].extend(stats["empty_examples"])
    aggregate["failures"] = aggregate["failures"][:20]
    aggregate["empty_examples"] = aggregate["empty_examples"][:20]
    pool_error = stats["pool_error"]

    if pool_error is None and big_tasks:
        print(f"big trees: {len(big_tasks)} queued ({big_skipped} existing skipped), serial")
        try:
            stats = _run_phase(big_tasks, 1, "Big trees (serial)", options, marker_dir)
        except KeyboardInterrupt:
            print("\ninterrupted; existing PNGs can be skipped on the next run", file=sys.stderr)
            active_inputs = _read_worker_markers(marker_dir)
            if active_inputs:
                print("\nlast in-flight inputs:", file=sys.stderr)
                for input_name in active_inputs:
                    print(f"  {input_name}", file=sys.stderr)
            shutil.rmtree(marker_dir, ignore_errors=True)
            return 130
        for key in ("rendered", "failed", "empty"):
            aggregate[key] += stats[key]
        aggregate["failures"].extend(stats["failures"])
        aggregate["empty_examples"].extend(stats["empty_examples"])
        aggregate["failures"] = aggregate["failures"][:20]
        aggregate["empty_examples"] = aggregate["empty_examples"][:20]
        pool_error = stats["pool_error"]

    elapsed = time.monotonic() - total_started
    total_rendered = aggregate["rendered"]
    print(
        f"done: rendered={total_rendered}, failed={aggregate['failed']}, "
        f"empty={aggregate['empty']}, invalid={len(invalid)}, "
        f"skipped={small_skipped + big_skipped}, elapsed={elapsed:.2f}s, "
        f"{total_rendered / elapsed if elapsed > 0 else 0:.2f} img/s, "
        f"workers={jobs}"
    )
    if aggregate["failures"]:
        print("\nfailures (first 20):", file=sys.stderr)
        for input_name, output_name, error in aggregate["failures"]:
            print(f"  {input_name} -> {output_name}: {error}", file=sys.stderr)
    if aggregate["empty_examples"]:
        print("\nempty/no-tree inputs (first 20):", file=sys.stderr)
        for input_name in aggregate["empty_examples"]:
            print(f"  {input_name}", file=sys.stderr)
    if invalid:
        print("\ninvalid inputs (first 20 from list_invalid.txt):", file=sys.stderr)
        for entry in invalid[:20]:
            print(f"  {entry}", file=sys.stderr)

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
                "A worker process was killed by the OS. Completed PNGs are kept; "
                "rerun with fewer --jobs or inspect the in-flight files.",
                file=sys.stderr,
            )
        return 1

    shutil.rmtree(marker_dir, ignore_errors=True)
    if aggregate["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
