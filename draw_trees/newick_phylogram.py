#!/usr/bin/env python3
"""Render a Newick tree as a rooted, support-annotated phylogram.

The program reads one Newick tree (or one tree selected from a multi-tree
file), reroots it at the midpoint by default, and writes a PNG next to the
input file (``tree.nwk`` -> ``tree.png``).

Examples
--------
    python newick_phylogram.py tree.nwk
    python newick_phylogram.py tree.nwk --title "My phylogeny" --dpi 300
    python newick_phylogram.py tree.nwk --outgroup TaxonA TaxonB
"""

from __future__ import annotations

import argparse
import logging
import math
import re
import sys
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")  # headless / server friendly; must precede pyplot import

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.cm import ScalarMappable
from matplotlib.colors import BoundaryNorm, ListedColormap, to_hex
from Bio import Phylo

__version__ = "1.3.0"

# ---------------------------------------------------------------------------
# Constants / global style
# ---------------------------------------------------------------------------

_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_SUPPORT_IN_COMMENT = re.compile(
    r"(?:support|bootstrap|posterior|prob(?:ability)?)\s*[=:]\s*("
    + _NUMBER
    + r")",
    re.IGNORECASE,
)
_PURE_NUMBER = re.compile(r"^\s*(" + _NUMBER + r")\s*%?\s*$")

_NO_SUPPORT_COLOR = "#000000"      # no support: use black, like root/leaf
_TERMINAL_COLOR = "#000000"       # terminal branches and root stub
_VERTICAL_COLOR = "#000000"       # root connector (no support)
_TEXT_COLOR = "#000000"
_MUTED_COLOR = "#6b7280"

# Five discrete support classes: 0-20, 20-40, 40-60, 60-80, 80-100.
# Colours stay saturated enough to remain visible as thin branch strokes.
_SUPPORT_COLOURS = ("#b91c1c", "#ea580c", "#ca8a04", "#84cc16", "#15803d")
_SUPPORT_CMAP = ListedColormap(_SUPPORT_COLOURS, name="support5")
_SUPPORT_BOUNDARIES = {
    "fraction": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    "percent": (0.0, 20.0, 40.0, 60.0, 80.0, 100.0),
}
_SUPPORT_TICK_LABELS = {
    "fraction": ("0", "0.2", "0.4", "0.6", "0.8", "1"),
    "percent": ("0", "20", "40", "60", "80", "100"),
}
_ROOT_STUB_FRACTION = 0.018

_CJK_FONT_CANDIDATES = (
    "Droid Sans Fallback",
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "Noto Sans CJK TC",
    "Source Han Sans SC",
    "Source Han Sans CN",
    "WenQuanYi Micro Hei",
    "WenQuanYi Zen Hei",
    "Microsoft YaHei",
    "SimHei",
    "PingFang SC",
    "Heiti SC",
    "Arial Unicode MS",
)

# Common locations help when Matplotlib's font cache predates the CJK font.
_CJK_FONT_FILES = (
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/truetype/droid/DroidSansFallback.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
)


class _BenignFontFallbackFilter(logging.Filter):
    """Hide noisy weight/style fallback notes, but keep family errors visible.

    Some CJK families (e.g. Source Han Sans SC, SimHei) ship no true bold or
    italic face.  Matplotlib falls back to weight 500/400 and logs a message
    for every such request.  That fallback is intentional and harmless; only
    those specific messages are filtered.  ``Font family ... not found``
    messages still pass through.
    """

    _IGNORED_MESSAGES = (
        "Failed to find font weight",
        "Failed to find font style",
        "Failed to find font stretch",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(needle in message for needle in self._IGNORED_MESSAGES)


def _install_font_warning_filter() -> None:
    logger = logging.getLogger("matplotlib.font_manager")
    if not any(isinstance(f, _BenignFontFallbackFilter) for f in logger.filters):
        logger.addFilter(_BenignFontFallbackFilter())


def _font_family_has_bold(name: str) -> bool:
    return any(
        font.name == name and int(font.weight) >= 600
        for font in font_manager.fontManager.ttflist
    )


def _available_font_families() -> list[str]:
    """Return a font fallback list containing only fonts that actually exist.

    Hard-coding a CJK family in ``rcParams`` makes Matplotlib emit
    ``findfont: Font family ... not found`` on systems without that font.  We
    therefore resolve the family list against the installed font cache and
    only advertise fonts that are present.  DejaVu Sans remains the primary
    Latin face; exactly one CJK family is used as fallback, preferring one
    that provides a real bold face so bold CJK titles do not fall back.
    """
    for font_path in _CJK_FONT_FILES:
        path = Path(font_path)
        if path.is_file():
            try:
                font_manager.fontManager.addfont(str(path))
            except Exception:
                pass

    available = {font.name for font in font_manager.fontManager.ttflist}
    families: list[str] = []
    if "DejaVu Sans" in available:
        families.append("DejaVu Sans")

    cjk_candidates = [
        candidate
        for candidate in _CJK_FONT_CANDIDATES
        if candidate in available and candidate not in families
    ]
    if cjk_candidates:
        # Prefer a family with a real bold face; otherwise use the first
        # available fallback.  Including only one CJK family avoids fallback
        # chains and duplicate warning noise.
        cjk_family = next(
            (name for name in cjk_candidates if _font_family_has_bold(name)),
            cjk_candidates[0],
        )
        families.append(cjk_family)

    if not families:
        # Last-resort generic family; do not include a concrete missing name.
        families = ["sans-serif"]
    return families


_install_font_warning_filter()
_FONT_FAMILIES = _available_font_families()

plt.rcParams.update(
    {
        # First family: Latin; remaining installed families: per-glyph fallback.
        "font.family": _FONT_FAMILIES,
        "font.sans-serif": _FONT_FAMILIES,
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "svg.fonttype": "none",
    }
)


# ---------------------------------------------------------------------------
# Parsing / validation helpers
# ---------------------------------------------------------------------------


_WARNINGS_ENABLED = True


def set_warnings_enabled(enabled: bool) -> None:
    """Enable/disable non-fatal warnings (batch workers disable them)."""
    global _WARNINGS_ENABLED
    _WARNINGS_ENABLED = bool(enabled)


def _warn(message: str) -> None:
    if _WARNINGS_ENABLED:
        print(f"[warning] {message}", file=sys.stderr)


def _as_float(value: object) -> float | None:
    """Return a finite, non-negative float, otherwise None."""
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result) or result < 0:
        return None
    return result


def _collapse_unary_nodes(tree: Phylo.BaseTree.Tree) -> None:
    """Remove unary nodes, which otherwise break midpoint rooting.

    A unary node contributes no information to an unrooted tree.  Biopython's
    ``root_at_midpoint`` can leave a phantom zero-length tip when the input
    root is unary, so normalise these nodes before rerooting.
    """

    def collapse_nonroot(node: Phylo.BaseTree.Clade) -> Phylo.BaseTree.Clade:
        if node.is_terminal():
            return node
        node.clades = [collapse_nonroot(child) for child in node.clades]
        while len(node.clades) == 1:
            child = node.clades[0]
            if node.branch_length is not None or child.branch_length is not None:
                child.branch_length = float(node.branch_length or 0.0) + float(
                    child.branch_length or 0.0
                )
            node = child
        return node

    root = tree.root
    while not root.is_terminal() and len(root.clades) == 1:
        root = root.clades[0]
        root.branch_length = None
    tree.root = root
    if not root.is_terminal():
        root.clades = [collapse_nonroot(child) for child in root.clades]


def _strip_outer_quotes(name: str) -> str:
    """Remove accidental surrounding quote/backslash artifacts from a label.

    Newick normally consumes quoting, but some exported files leave a literal
    quote pair in the parsed name (``'A'``, ``\\'A\\'``, ``"A"``, or a stray
    trailing quote).  We strip quote and backslash characters only at the two
    ends, so an apostrophe inside a name (``O'Brien``) is preserved.
    """
    text = str(name).strip()
    while True:
        cleaned = text.strip().strip("'\"\\")
        if cleaned == text:
            break
        text = cleaned
    return text


def _clean_leaf_names(tree: Phylo.BaseTree.Tree) -> None:
    for tip in tree.get_terminals():
        if tip.name is None:
            continue
        cleaned = _strip_outer_quotes(str(tip.name))
        tip.name = cleaned or None


def _extract_supports(tree: Phylo.BaseTree.Tree) -> None:
    """Populate ``clade.confidence`` from common Newick support conventions.

    Biopython already reads a numeric internal label into ``confidence``.
    This also accepts comments such as ``[&support=95]`` or ``[95]`` and
    numeric internal names not handled by the parser.
    """
    root = tree.root
    for clade in tree.find_clades():
        if clade is root or clade.is_terminal():
            continue

        value: float | None = None

        if clade.confidence is not None:
            value = _as_float(clade.confidence)

        if value is None:
            comment = getattr(clade, "comment", None) or ""
            match = _SUPPORT_IN_COMMENT.search(comment)
            if match is None:
                match = _PURE_NUMBER.fullmatch(str(comment).strip().lstrip("&"))
            if match is not None:
                value = _as_float(match.group(1))

        if value is None and clade.name:
            match = _PURE_NUMBER.fullmatch(str(clade.name))
            if match is not None:
                value = _as_float(match.group(1))
                clade.name = None

        if value is not None:
            clade.confidence = value
        elif clade.confidence is not None:
            # Invalid (e.g. negative or NaN) confidence: do not visualise it.
            clade.confidence = None


def _prepare_branch_lengths(tree: Phylo.BaseTree.Tree) -> tuple[str, str | None]:
    """Ensure usable branch lengths and report the drawing mode.

    Returns
    -------
    mode
        ``"phylogram"`` when every non-root edge has a valid length and the
        total length is positive; otherwise ``"cladogram"``.
    reason
        Human-readable reason when falling back to unit branch lengths.
    """
    root = tree.root
    root.branch_length = None
    edges = [clade for clade in tree.find_clades() if clade is not root]
    if not edges:
        return "cladogram", "single-tip tree"

    raw_lengths = [clade.branch_length for clade in edges]
    invalid = [
        value
        for value in raw_lengths
        if value is not None
        and (not math.isfinite(float(value)) or float(value) < 0)
    ]
    missing = [value for value in raw_lengths if value is None]

    if not invalid and not missing:
        lengths = [float(value) for value in raw_lengths if value is not None]
        if sum(lengths) > 0 and max(lengths) > 0:
            return "phylogram", None
        reason = "all branch lengths are zero"
    elif invalid:
        reason = "negative or non-finite branch lengths found"
    elif len(missing) == len(raw_lengths):
        reason = "branch lengths are missing"
    else:
        reason = "some branch lengths are missing"

    # A mixed set of supplied/absent lengths cannot be displayed honestly as
    # a phylogram.  Fall back to topology with one unit per edge.
    for clade in edges:
        clade.branch_length = 1.0
    return "cladogram", reason


def _midpoint_reroot(tree: Phylo.BaseTree.Tree) -> None:
    """Reroot ``tree`` at the midpoint of its longest leaf-to-leaf path.

    This is a small graph implementation rather than a call to Biopython's
    ``root_at_midpoint``.  Biopython's helper is convenient but can duplicate
    or inflate branch lengths for some small/star trees; working on an explicit
    adjacency graph lets us preserve edge lengths and edge-associated support
    exactly.
    """
    root = tree.root
    clades = list(tree.find_clades(order="preorder"))
    n = len(clades)
    if n <= 1:
        return
    index = {id(clade): i for i, clade in enumerate(clades)}
    names = [clade.name for clade in clades]
    degrees = [len(clade.clades) for clade in clades]
    is_leaf = [degree == 0 for degree in degrees]

    # adjacency[u] = list of (neighbour, length, support-on-edge)
    adjacency: list[list[tuple[int, float, float | None]]] = [[] for _ in range(n)]
    neighbor_count = [0] * n
    for i, clade in enumerate(clades):
        for child in clade.clades:
            j = index[id(child)]
            length = float(child.branch_length or 0.0)
            support = None
            if not child.is_terminal() and child is not root:
                support = _as_float(child.confidence)
            adjacency[i].append((j, length, support))
            adjacency[j].append((i, length, support))
            neighbor_count[i] += 1
            neighbor_count[j] += 1

    # --- tree diameter via a linear-time downward-height DP -----------------
    parent = [-2] * n
    parent[0] = -1
    order = [0]
    for u in order:
        for v, _length, _support in adjacency[u]:
            if v == parent[u]:
                continue
            parent[v] = u
            order.append(v)
    if len(order) != n:
        raise ValueError("tree graph is not connected")

    best_distance = [0.0] * n
    best_leaf = list(range(n))
    diameter = 0.0
    diameter_a = diameter_b = 0

    for u in reversed(order):
        candidates: list[tuple[float, int]] = []
        for v, length, _support in adjacency[u]:
            if parent[v] == u:
                candidates.append((length + best_distance[v], best_leaf[v]))
        candidates.sort(key=lambda item: item[0], reverse=True)
        if candidates:
            best_distance[u], best_leaf[u] = candidates[0]
            if len(candidates) > 1:
                through_u = candidates[0][0] + candidates[1][0]
                if through_u > diameter:
                    diameter = through_u
                    diameter_a, diameter_b = candidates[0][1], candidates[1][1]
        else:
            # A leaf, or a unary node after normalisation.
            best_distance[u] = 0.0
            best_leaf[u] = u

    if diameter <= 1e-15:
        # Degenerate tree (all edges zero).  Root at an internal node if one
        # exists so the result is still a valid drawing.
        center = next((i for i in range(n) if neighbor_count[i] > 1), 0)
        diameter_a = diameter_b = center

    # --- reconstruct the diameter path ---------------------------------------
    previous = [-2] * n
    previous_edge = [0.0] * n
    previous[ diameter_a] = -1
    queue = [diameter_a]
    for u in queue:
        if u == diameter_b:
            break
        for v, length, _support in adjacency[u]:
            if previous[v] != -2:
                continue
            previous[v] = u
            previous_edge[v] = length
            queue.append(v)
    if previous[diameter_b] == -2:
        raise ValueError("could not trace the tree diameter")

    path_nodes: list[int] = []
    path_lengths: list[float] = []
    cursor = diameter_b
    while cursor != -1:
        path_nodes.append(cursor)
        if previous[cursor] != -1:
            path_lengths.append(previous_edge[cursor])
        cursor = previous[cursor]
    path_nodes.reverse()
    path_lengths.reverse()
    total = sum(path_lengths)

    def build(start: int, blocked: int, length: float | None,
              support: float | None) -> Phylo.BaseTree.Clade:
        children: list[Phylo.BaseTree.Clade] = []
        for nxt, edge_length, edge_support in adjacency[start]:
            if nxt == blocked:
                continue
            children.append(build(nxt, start, edge_length, edge_support))
        clade = Phylo.BaseTree.Clade(
            branch_length=length,
            name=names[start] or None,
            clades=children,
        )
        if support is not None:
            clade.confidence = support
        return clade

    if diameter <= 1e-15:
        new_root = build(center, -1, None, None)
        new_root.branch_length = None
        new_root.confidence = None
        tree.root = new_root
        tree.rooted = True
        return

    target = total / 2.0
    tolerance = max(1e-12, total * 1e-12)
    cumulative = 0.0
    split_u = split_v = -1
    split_fraction = 0.0
    for index_on_path, (u, v) in enumerate(
        zip(path_nodes, path_nodes[1:])
    ):
        edge_length = path_lengths[index_on_path]
        if target <= cumulative + tolerance:
            # Centre coincides with the node at the start of this edge.
            split_u = split_v = u
            break
        if target >= cumulative + edge_length - tolerance:
            cumulative += edge_length
            continue
        split_u, split_v = u, v
        split_fraction = target - cumulative
        break
    else:
        split_u = split_v = path_nodes[-1]

    if split_u == split_v:
        new_root = build(split_u, -1, None, None)
        new_root.branch_length = None
        new_root.confidence = None
        tree.root = new_root
        tree.rooted = True
        return

    # The midpoint lies inside edge split_u--split_v.  Recover that edge's
    # support and attach it once to the larger of the two resulting clades.
    edge_support = None
    for v, _length, support in adjacency[split_u]:
        if v == split_v:
            edge_support = support
            break

    def side_leaf_count(start: int, blocked: int) -> int:
        count = 0
        stack = [(start, blocked)]
        while stack:
            node, prev = stack.pop()
            if is_leaf[node]:
                count += 1
            for nxt, _length, _support in adjacency[node]:
                if nxt != prev:
                    stack.append((nxt, node))
        return count

    left_count = side_leaf_count(split_u, split_v)
    right_count = side_leaf_count(split_v, split_u)
    support_u = edge_support if left_count >= right_count else None
    support_v = edge_support if right_count > left_count else None

    for index_on_path, (u, v) in enumerate(zip(path_nodes, path_nodes[1:])):
        if u == split_u and v == split_v:
            edge_length = path_lengths[index_on_path]
            break
    else:
        raise ValueError("midpoint edge not found on diameter path")

    left = build(split_u, split_v, split_fraction, support_u)
    right = build(split_v, split_u, edge_length - split_fraction, support_v)
    new_root = Phylo.BaseTree.Clade(clades=[left, right])
    tree.root = new_root
    tree.rooted = True


def _reroot_tree(
    tree: Phylo.BaseTree.Tree,
    outgroup: Sequence[str] | None,
) -> tuple[str, str]:
    """Reroot in place. Return (short label, longer description)."""
    tips = tree.get_terminals()
    if len(tips) < 2:
        return "not rerooted", "single-tip tree"

    root = tree.root
    root.branch_length = None

    if outgroup:
        available = {str(clade.name) for clade in tips if clade.name}
        missing = [name for name in outgroup if name not in available]
        if missing:
            raise ValueError(
                "outgroup taxon/taxa not found: " + ", ".join(missing)
            )
        tree.root_with_outgroup(list(outgroup))
        tree.root.branch_length = None
        return "outgroup-rooted", "rooted with outgroup: " + ", ".join(outgroup)

    try:
        _midpoint_reroot(tree)
        tree.root.branch_length = None
        return "midpoint-rooted", "rooted at the midpoint of the longest leaf path"
    except Exception as exc:  # defensive fallback
        _warn(f"midpoint rooting failed ({exc}); using a leaf-outgroup fallback")
        first_tip = tips[0].name
        if first_tip:
            tree.root_with_outgroup(first_tip)
            tree.root.branch_length = None
            return "outgroup-rooted (fallback)", "midpoint failed; rooted on the first tip"
        raise


def _read_tree(path: Path, index: int) -> tuple[Phylo.BaseTree.Tree, int]:
    if not path.is_file():
        raise FileNotFoundError(f"input file not found: {path}")
    try:
        trees = list(Phylo.parse(str(path), "newick"))
    except Exception as exc:
        raise ValueError(f"could not parse Newick file {path}: {exc}") from exc
    if not trees:
        raise ValueError(f"no trees found in {path}")
    if index < 0 or index >= len(trees):
        raise ValueError(
            f"--tree-index {index} is out of range; file contains "
            f"{len(trees)} tree(s)"
        )
    if len(trees) > 1:
        _warn(
            f"{path.name} contains {len(trees)} trees; using tree index {index} "
            "(use --tree-index to choose another)"
        )
    return trees[index], len(trees)


# ---------------------------------------------------------------------------
# Tree geometry and support scale
# ---------------------------------------------------------------------------


def _ladderize(tree: Phylo.BaseTree.Tree) -> None:
    if not tree.root.is_terminal():
        tree.ladderize(reverse=False)


def _assign_positions(tree: Phylo.BaseTree.Tree) -> tuple[float, int]:
    """Assign ``_x``/``_y`` to every clade. Return (max_x, n_tips)."""
    root = tree.root
    tips = tree.get_terminals()
    n_tips = len(tips)

    # Position tips from top to bottom.  Matplotlib's y axis points upwards,
    # so the first tip receives the largest y value.
    for index, tip in enumerate(tips):
        tip._y = float(n_tips - 1 - index)
    if root.is_terminal():
        root._y = 0.0

    def set_internal_y(node: Phylo.BaseTree.Clade) -> float:
        if node.is_terminal():
            return node._y
        ys = [set_internal_y(child) for child in node.clades]
        node._y = sum(ys) / len(ys)
        return node._y

    set_internal_y(root)

    stack: list[tuple[Phylo.BaseTree.Clade, float]] = [(root, 0.0)]
    max_x = 0.0
    while stack:
        node, x = stack.pop()
        node._x = x
        max_x = max(max_x, x)
        for child in node.clades:
            length = float(child.branch_length or 0.0)
            stack.append((child, x + length))

    return max_x, n_tips


def _support_scale(
    values: Iterable[float], requested: str
) -> tuple[str, float, float] | None:
    vals = [value for value in values if math.isfinite(value) and value >= 0]
    if not vals:
        return None
    if requested == "fraction":
        return "fraction", 0.0, 1.0
    if requested == "percent":
        return "percent", 0.0, 100.0

    # auto: a support set entirely within [0, 1] is treated as a fraction.
    if max(vals) <= 1.0 + 1e-12:
        return "fraction", 0.0, 1.0
    if min(vals) <= 1.0 < max(vals):
        _warn(
            "support values span both 0-1 and >1; treating all as percentages. "
            "Use --support-scale fraction/percent to override."
        )
    return "percent", 0.0, 100.0


def _support_values(tree: Phylo.BaseTree.Tree) -> list[float]:
    root = tree.root
    values: list[float] = []
    root_support = _as_float(root.confidence) if root.confidence is not None else None
    if root_support is not None:
        values.append(root_support)
    for clade in tree.find_clades():
        if clade is root or clade.is_terminal() or clade.confidence is None:
            continue
        value = _as_float(clade.confidence)
        if value is not None:
            values.append(value)
    return values


def _format_support(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _nice_scale(raw: float) -> float:
    """Return a 1/2/5 x 10^n value near ``raw``."""
    if raw <= 0 or not math.isfinite(raw):
        return 1.0
    exponent = math.floor(math.log10(raw))
    base = 10.0**exponent
    fraction = raw / base
    if fraction < 1.5:
        nice = 1.0
    elif fraction < 3.5:
        nice = 2.0
    elif fraction < 7.5:
        nice = 5.0
    else:
        nice = 10.0
    return nice * base


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def _adaptive_figure_size(
    n_tips: int,
    n_nodes: int,
    max_label_length: int,
    topology_only: bool = False,
) -> tuple[float, float]:
    # Height is deliberately driven by the number of tips/nodes so that labels
    # and support numbers remain legible as the tree grows.
    height = max(
        3.4,
        0.28 * n_tips + 1.8,
        0.10 * n_nodes + 1.8,
    )
    width = max(
        8.0,
        min(18.0, 7.0 + 0.050 * n_tips + 0.080 * max_label_length),
    )
    if topology_only:
        # Unit-branch trees have no natural horizontal scale.  Give them extra
        # width so the topology does not look cramped.
        width = min(20.0, max(width + 2.5, 10.0 + 0.05 * n_tips))
    return width, height


def _branch_style(
    clade: Phylo.BaseTree.Clade,
    root: Phylo.BaseTree.Clade,
    scale_info: tuple[str, float, float] | None,
    norm: BoundaryNorm | None,
    cmap,
) -> tuple[str, float, bool]:
    """Return (colour, linewidth, has_support) for the branch above clade."""
    if clade is root or clade.is_terminal():
        return _TERMINAL_COLOR, 1.05, False
    support = _as_float(clade.confidence)
    if scale_info is None or support is None or norm is None:
        return _NO_SUPPORT_COLOR, 1.15, False
    colour = to_hex(cmap(norm(support)))
    return colour, 1.75, True


def _plot_tree(
    ax: plt.Axes,
    tree: Phylo.BaseTree.Tree,
    scale_info: tuple[str, float, float] | None,
    norm: BoundaryNorm | None,
    cmap,
    leaf_fontsize: float,
    support_fontsize: float,
    span: float,
    branch_mode: str,
    branch_reason: str | None,
) -> None:
    root = tree.root
    label_pad = max(span * 0.010, 1e-6)
    support_pad_x = max(span * 0.008, 1e-6)
    support_pad_y = 0.13

    root_support = _as_float(root.confidence) if root.confidence is not None else None

    # --- rectangular branches -------------------------------------------------
    def draw_node(node: Phylo.BaseTree.Clade) -> None:
        if node.is_terminal():
            return

        if node is root:
            connector_colour = _VERTICAL_COLOR
            connector_width = 1.20
        else:
            connector_colour, parent_width, parent_has_support = _branch_style(
                node, root, scale_info, norm, cmap
            )
            connector_width = parent_width * 0.78 if parent_has_support else 1.05

        child_ys = [child._y for child in node.clades]
        if len(child_ys) > 1:
            ax.plot(
                [node._x, node._x],
                [min(child_ys), max(child_ys)],
                color=connector_colour,
                linewidth=connector_width,
                solid_capstyle="round",
                zorder=2,
            )

        for child in node.clades:
            colour, linewidth, has_support = _branch_style(
                child, root, scale_info, norm, cmap
            )
            ax.plot(
                [node._x, child._x],
                [child._y, child._y],
                color=colour,
                linewidth=linewidth,
                solid_capstyle="round",
                zorder=3,
            )

            if not child.is_terminal():
                if has_support:
                    ax.scatter(
                        [child._x],
                        [child._y],
                        s=max(9.0, leaf_fontsize * 1.45),
                        c=[colour],
                        edgecolors="white",
                        linewidths=0.45,
                        zorder=5,
                        clip_on=False,
                    )
                    ax.text(
                        child._x - support_pad_x,
                        child._y + support_pad_y,
                        _format_support(float(child.confidence)),
                        ha="right",
                        va="bottom",
                        fontsize=support_fontsize,
                        fontweight="semibold",
                        color=_TEXT_COLOR,
                        zorder=6,
                        clip_on=False,
                        bbox={
                            "boxstyle": "round,pad=0.14",
                            "facecolor": "white",
                            "edgecolor": "none",
                            "alpha": 0.88,
                        },
                    )
                draw_node(child)

    draw_node(root)

    if root.is_terminal():
        ax.scatter([root._x], [root._y], s=18, c=[_TERMINAL_COLOR], zorder=5)

    # Outgroup rooting can put a meaningful support value on the root itself.
    # Highlight it at the root rather than silently dropping it.
    if root_support is not None and scale_info is not None and norm is not None:
        root_support_colour = to_hex(cmap(norm(root_support)))
        ax.scatter(
            [root._x],
            [root._y],
            s=max(12.0, leaf_fontsize * 1.8),
            c=[root_support_colour],
            edgecolors="white",
            linewidths=0.55,
            zorder=7,
            clip_on=False,
        )
        ax.annotate(
            f"root {_format_support(root_support)}",
            xy=(root._x, root._y),
            xytext=(-7, 7),
            textcoords="offset points",
            ha="right",
            va="bottom",
            fontsize=support_fontsize,
            fontweight="semibold",
            color=_TEXT_COLOR,
            zorder=8,
            annotation_clip=False,
            bbox={
                "boxstyle": "round,pad=0.16",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.9,
            },
        )

    # --- tip labels -----------------------------------------------------------
    for tip in tree.get_terminals():
        label = str(tip.name) if tip.name else "unnamed taxon"
        ax.text(
            tip._x + label_pad,
            tip._y,
            label,
            ha="left",
            va="center",
            fontsize=leaf_fontsize,
            fontstyle="italic",
            color=_TEXT_COLOR,
            zorder=6,
            clip_on=False,
        )

    # --- root stub and axes limits -------------------------------------------
    n_tips = len(tree.get_terminals())
    if n_tips > 1:
        stub = _ROOT_STUB_FRACTION * span
        ax.plot(
            [-stub, 0.0],
            [root._y, root._y],
            color=_TERMINAL_COLOR,
            linewidth=1.20,
            solid_capstyle="round",
            zorder=3,
            clip_on=False,
        )
    ax.set_xlim(-0.04 * span, 1.06 * span)
    if n_tips <= 1:
        ax.set_ylim(-0.8, 0.8)
    else:
        bottom_margin = min(1.20, 0.45 + 0.12 * n_tips)
        top_margin = min(0.75, 0.25 + 0.08 * n_tips)
        ax.set_ylim(-bottom_margin, (n_tips - 1) + top_margin)
    ax.set_axis_off()

    # --- scale bar / topology note -------------------------------------------
    if n_tips > 1:
        bottom_margin = min(1.20, 0.45 + 0.12 * n_tips)
        y_bar = -bottom_margin + 0.28
        if branch_mode == "phylogram" and span > 0:
            step = _nice_scale(span * 0.18)
            ax.plot(
                [0.0, step],
                [y_bar, y_bar],
                color=_TEXT_COLOR,
                linewidth=1.6,
                solid_capstyle="butt",
                zorder=4,
            )
            for x_tick in (0.0, step):
                ax.plot(
                    [x_tick, x_tick],
                    [y_bar - 0.08, y_bar + 0.08],
                    color=_TEXT_COLOR,
                    linewidth=1.1,
                    zorder=4,
                )
            ax.text(
                step * 1.10,
                y_bar,
                f"{step:g} branch length",
                ha="left",
                va="center",
                fontsize=max(6.5, leaf_fontsize - 2.1),
                color=_MUTED_COLOR,
            )
        else:
            note = "topology only"
            if branch_reason:
                note += f" — {branch_reason}"
            ax.text(
                0.0,
                y_bar,
                note,
                ha="left",
                va="center",
                fontsize=max(6.5, leaf_fontsize - 2.0),
                color=_MUTED_COLOR,
                style="italic",
            )


def _render(
    tree: Phylo.BaseTree.Tree,
    out_path: Path,
    *,
    title: str,
    source_name: str,
    root_label: str,
    root_description: str,
    branch_mode: str,
    branch_reason: str | None,
    dpi: int,
    support_scale: str,
    png_compress_level: int = 6,
) -> dict[str, object]:
    _clean_leaf_names(tree)
    span, n_tips = _assign_positions(tree)
    if span <= 0:
        span = 1.0

    # Assign fallback names after rerooting (only for display).
    for index, tip in enumerate(tree.get_terminals(), start=1):
        if not tip.name:
            tip.name = f"taxon_{index}"

    n_nodes = sum(1 for _ in tree.find_clades())
    n_internal = sum(
        1 for clade in tree.get_nonterminals() if clade is not tree.root
    )
    max_label_length = max(
        (len(str(tip.name)) for tip in tree.get_terminals()), default=1
    )
    width, height = _adaptive_figure_size(
        n_tips,
        n_nodes,
        max_label_length,
        topology_only=branch_mode == "cladogram",
    )

    values = _support_values(tree)
    scale_info = _support_scale(values, support_scale)
    cmap = _SUPPORT_CMAP
    norm: BoundaryNorm | None = None
    boundaries: tuple[float, ...] | None = None
    tick_labels: tuple[str, ...] | None = None
    if scale_info is not None:
        kind = scale_info[0]
        boundaries = _SUPPORT_BOUNDARIES[kind]
        tick_labels = _SUPPORT_TICK_LABELS[kind]
        norm = BoundaryNorm(boundaries, ncolors=cmap.N, clip=True)

    fig = plt.figure(figsize=(width, height), facecolor="white")
    # Keep the top furniture (title, subtitle, colour bar) at a roughly
    # constant physical height rather than letting it grow on tall figures.
    axes_bottom = 0.30 / height
    axes_top = 1.0 - 0.80 / height
    ax = fig.add_axes([0.045, axes_bottom, 0.94, axes_top - axes_bottom])

    leaf_fontsize = max(7.0, min(10.5, 11.4 - 0.043 * n_tips))
    support_fontsize = max(5.4, leaf_fontsize - 2.0)

    _plot_tree(
        ax,
        tree,
        scale_info,
        norm,
        cmap,
        leaf_fontsize,
        support_fontsize,
        span,
        branch_mode,
        branch_reason,
    )

    # --- titles ---------------------------------------------------------------
    title_fontsize = min(19.0, 16.5 + max(0.0, height - 8.0) * 0.20)
    fig.text(
        0.045,
        1.0 - 0.055 / height,
        title,
        ha="left",
        va="top",
        fontsize=title_fontsize,
        fontweight="bold",
        color=_TEXT_COLOR,
    )

    mode_text = (
        "branch lengths shown"
        if branch_mode == "phylogram"
        else "topology only"
    )
    subtitle_parts = [
        f"{n_tips} taxa",
        f"{n_internal} internal nodes",
        root_label,
        mode_text,
    ]
    subtitle_fontsize = min(10.8, 9.4 + max(0.0, height - 8.0) * 0.10)
    fig.text(
        0.045,
        1.0 - 0.335 / height,
        " · ".join(subtitle_parts),
        ha="left",
        va="top",
        fontsize=subtitle_fontsize,
        color=_MUTED_COLOR,
    )

    # --- support colour legend ------------------------------------------------
    if scale_info is not None and norm is not None and boundaries is not None:
        sm = ScalarMappable(norm=norm, cmap=cmap)
        sm.set_array([])
        cax = fig.add_axes(
            [0.675, 1.0 - 0.68 / height, 0.295, 0.090 / height]
        )
        colorbar = fig.colorbar(
            sm,
            cax=cax,
            orientation="horizontal",
            boundaries=boundaries,
            ticks=boundaries,
            spacing="proportional",
            drawedges=True,
        )
        colorbar.ax.set_xticklabels(tick_labels or [])
        colorbar.ax.tick_params(
            labelsize=6.8, length=2.0, pad=1.2, colors=_MUTED_COLOR
        )
        if colorbar.dividers is not None:
            colorbar.dividers.set_color("white")
            colorbar.dividers.set_linewidth(0.8)
        colorbar.outline.set_edgecolor("#d1d5db")
        colorbar.outline.set_linewidth(0.6)
        scale_note = (
            "Support (0–1 scale)"
            if scale_info[0] == "fraction"
            else "Support (%)"
        )
        cax.set_title(
            scale_note,
            fontsize=min(8.4, 7.6 + max(0.0, height - 8.0) * 0.07),
            color=_MUTED_COLOR,
            loc="left",
            pad=3.2,
        )

    # --- provenance / caveat --------------------------------------------------
    fig.text(
        0.985,
        0.060 / height,
        f"source: {source_name}",
        ha="right",
        va="bottom",
        fontsize=6.8,
        color="#9ca3af",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "Title": title,
        "Software": f"newick_phylogram.py {__version__} (Biopython + Matplotlib)",
        "Description": root_description,
    }
    if branch_reason:
        metadata["BranchLengthNote"] = branch_reason
    fig.savefig(
        out_path,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.16,
        facecolor="white",
        metadata=metadata,
        pil_kwargs={"compress_level": png_compress_level},
    )
    plt.close(fig)

    return {
        "taxa": n_tips,
        "nodes": n_nodes,
        "support_values": len(values),
        "width_in": round(width, 2),
        "height_in": round(height, 2),
        "rooting": root_label,
        "branch_mode": branch_mode,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="newick_phylogram.py",
        description=(
            "Render a Newick tree as a support-annotated phylogram. The tree is "
            "rerooted at its midpoint by default; output defaults to the input "
            "filename with a .png suffix."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("newick", type=Path, help="input Newick (.nwk/.tree) file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="output PNG path (default: <input stem>.png)",
    )
    parser.add_argument("--title", default=None, help="figure title")
    parser.add_argument(
        "--outgroup",
        nargs="+",
        metavar="TAXON",
        default=None,
        help="root on this taxon / these taxa instead of midpoint rooting",
    )
    parser.add_argument(
        "--tree-index",
        type=int,
        default=0,
        help="zero-based index of the tree in a multi-tree Newick file (default: 0)",
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
        help="interpret supports as 0-1 fractions or 0-100 percentages (default: auto)",
    )
    parser.add_argument(
        "--no-ladderize",
        action="store_true",
        help="keep the child order produced by rerooting",
    )
    parser.add_argument(
        "--png-compress-level",
        type=int,
        choices=range(10),
        default=6,
        metavar="{0-9}",
        help=(
            "PNG zlib level: 0=fastest/largest, 9=slowest/smallest "
            "(default: 6)"
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def _split_outgroup(values: Sequence[str] | None) -> list[str] | None:
    """Normalise the outgroup list without altering taxon names.

    Multiple taxa are supplied as separate command-line arguments, so names
    may themselves contain commas or spaces (quote them in the shell).
    """
    if not values:
        return None
    return [_strip_outer_quotes(value) for value in values]


def render_newick_file(
    input_path: Path,
    output_path: Path,
    *,
    title: str | None = None,
    tree_index: int = 0,
    outgroup: Sequence[str] | None = None,
    dpi: int = 200,
    support_scale: str = "auto",
    no_ladderize: bool = False,
    png_compress_level: int = 6,
) -> dict[str, object]:
    """Run the complete parse/reroot/draw pipeline for one Newick file."""
    tree, _ = _read_tree(input_path, tree_index)
    _extract_supports(tree)
    _clean_leaf_names(tree)
    _collapse_unary_nodes(tree)
    branch_mode, branch_reason = _prepare_branch_lengths(tree)
    if branch_mode == "cladogram":
        _warn(
            "drawing topology with unit branch lengths"
            + (f" ({branch_reason})" if branch_reason else "")
        )

    root_label, root_description = _reroot_tree(
        tree, _split_outgroup(outgroup)
    )

    # Splitting an edge at the midpoint can leave a unary node (notably for a
    # two-tip tree).  Collapse these so the drawing has clean bifurcations.
    _collapse_unary_nodes(tree)
    if tree.root.branch_length is not None:
        tree.root.branch_length = None

    if not no_ladderize:
        _ladderize(tree)

    figure_title = (title or "").strip() or input_path.stem or "phylogram"
    return _render(
        tree,
        output_path,
        title=figure_title,
        source_name=input_path.name,
        root_label=root_label,
        root_description=root_description,
        branch_mode=branch_mode,
        branch_reason=branch_reason,
        dpi=dpi,
        support_scale=support_scale,
        png_compress_level=png_compress_level,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.dpi < 200 or args.dpi > 1200:
        parser.error("--dpi must be between 200 and 1200")

    input_path = args.newick
    output_path = args.output
    if output_path is None:
        output_path = input_path.with_suffix(".png")
    elif output_path.suffix == "":
        output_path = output_path.with_suffix(".png")
    elif output_path.suffix.lower() != ".png":
        print("error: --output must have a .png suffix", file=sys.stderr)
        return 2

    try:
        summary = render_newick_file(
            input_path,
            output_path,
            title=args.title,
            tree_index=args.tree_index,
            outgroup=args.outgroup,
            dpi=args.dpi,
            support_scale=args.support_scale,
            no_ladderize=args.no_ladderize,
            png_compress_level=args.png_compress_level,
        )
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: failed to draw tree: {exc}", file=sys.stderr)
        return 1

    print(
        f"wrote {output_path}  "
        f"({summary['taxa']} taxa, {summary['nodes']} nodes, "
        f"{summary['support_values']} supports, "
        f"{summary['width_in']} x {summary['height_in']} in, "
        f"{summary['rooting']}, {summary['branch_mode']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
