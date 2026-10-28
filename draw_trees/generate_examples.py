#!/usr/bin/env python3
"""Create the demonstration Newick files used by this project.

Running this script also renders every example with newick_phylogram.py.
The generated files deliberately cover:

* bootstrap support (0-100) and posterior support (0-1)
* unrooted/trifurcating input, no support values
* missing branch lengths and all-zero branch lengths
* quoted taxon names and a polytomy
* support stored in Newick comments
* a larger 40-taxon tree (automatic height growth)
* a minimal two-taxon tree
"""

from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE / "examples"
PROGRAM = HERE / "newick_phylogram.py"


def _balanced_tree(names: list[str], rng: random.Random, depth: int = 0) -> str:
    """Return a random, reasonably balanced Newick subtree with supports."""
    if len(names) == 1:
        length = rng.uniform(0.04, 0.22)
        return f"{names[0]}:{length:.3f}"

    midpoint = len(names) // 2
    left = _balanced_tree(names[:midpoint], rng, depth + 1)
    right = _balanced_tree(names[midpoint:], rng, depth + 1)
    length = rng.uniform(0.035, 0.14)
    support = int(round(min(100, max(45, rng.gauss(88, 11)))))
    return f"({left},{right}){support}:{length:.3f}"


def _large_tree() -> str:
    rng = random.Random(20261028)
    names = [f"Sp{index:02d}" for index in range(1, 41)]
    return _balanced_tree(names, rng) + ";"


EXAMPLES_DATA: list[tuple[str, str, str, list[str]]] = [
    (
        "01_bootstrap_phylogram.nwk",
        "Bootstrap supports (9 taxa)",
        "(((A:0.12,B:0.15)92:0.18,(C:0.10,D:0.13)76:0.22)84:0.20,"
        "((E:0.11,F:0.14)95:0.16,(G:0.12,H:0.10)68:0.24)72:0.19,"
        "M_untested:0.55);",
        [],
    ),
    (
        "02_posterior_phylogram.nwk",
        "Posterior supports, 0–1 scale",
        "(((A:0.045,B:0.052)0.98:0.060,(C:0.038,D:0.041)0.91:0.070)0.89:0.050,"
        "((E:0.043,F:0.039)1.0:0.055,(G:0.048,H:0.044)0.84:0.065)0.95:0.050,"
        "(I:0.036,J:0.040)0.72:0.080);",
        [],
    ),
    (
        "03_unrooted_no_support.nwk",
        "Unrooted input, no supports",
        "((((A:0.12,B:0.15):0.08,C:0.11):0.06,D:0.14):0.09,"
        "(E:0.13,F:0.10):0.11,(G:0.09,H:0.12):0.10);",
        [],
    ),
    (
        "04_no_branch_lengths.nwk",
        "No branch lengths, bootstrap labels",
        "((((A,B)98,(C,D)87)91,(E,F)76)65,((G,H)99,I)80);",
        [],
    ),
    (
        "05_partial_branch_lengths.nwk",
        "Incomplete branch lengths",
        "((A:0.10,B)90:0.20,((C:0.15,D:0.12)85:0.08,E)70,"
        "(F:0.09,G:0.11,H:0.13)55);",
        [],
    ),
    (
        "06_quoted_names_polytomy.nwk",
        "Quoted names and a polytomy",
        "(('Homo sapiens':0.12,'Pan paniscus':0.14)96:0.08,"
        "('Gorilla gorilla':0.11,'Pongo abelii':0.16,'Macaca mulatta':0.18)72:0.10,"
        "('Mus musculus':0.20,'Rattus norvegicus':0.19)89:0.12);",
        [],
    ),
    (
        "07_comment_support.nwk",
        "Supports in Newick comments",
        "(((A:0.12,B:0.18)[&support=0.95]:0.20,"
        "(C:0.16,D:0.11)[&bootstrap=0.81]:0.15)0.86:0.12,"
        "(E:0.14,F:0.17)[&posterior=0.73]:0.18,G:0.30);",
        [],
    ),
    (
        "08_large_tree_40_taxa.nwk",
        "Large tree (40 taxa)",
        _large_tree(),
        [],
    ),
    (
        "09_two_taxa.nwk",
        "Two-taxon tree",
        "(Taxon_A:0.42,Taxon_B:0.38);",
        [],
    ),
    (
        "10_all_zero_lengths.nwk",
        "All-zero branch lengths",
        "((((A:0,B:0):0,(C:0,D:0):0)90:0,"
        "((E:0,F:0):0,(G:0,H:0):0)80:0):0);",
        [],
    ),
]


def main() -> int:
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    failures = 0
    for filename, title, newick, extra_args in EXAMPLES_DATA:
        newick_path = EXAMPLES / filename
        newick_path.write_text(newick + "\n", encoding="utf-8")
        command = [
            sys.executable,
            str(PROGRAM),
            str(newick_path),
            "--title",
            title,
            *extra_args,
        ]
        print(f"$ {' '.join(command)}")
        result = subprocess.run(command, cwd=HERE)
        if result.returncode != 0:
            failures += 1
            print(f"  -> failed with exit code {result.returncode}", file=sys.stderr)
    if failures:
        print(f"{failures} example(s) failed", file=sys.stderr)
        return 1
    print(f"\nAll {len(EXAMPLES_DATA)} examples rendered in {EXAMPLES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
