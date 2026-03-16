# functions\create_graph_images.py
# Save a heatmap chart of Pixela pixel data
# -----------------------------------------------------------------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch
import numpy as np
from datetime import datetime, timedelta
import os
from pathlib import Path
import sys

try:
    from helpers.json_manager import get_pixel_dict, get_graph_color
    
except ModuleNotFoundError:
    # Allow running this file directly: add project root to sys.path
    _project_root = Path(__file__).resolve().parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    from helpers.json_manager import get_pixel_dict, get_graph_color

BASE_DIR = str(Path(__file__).resolve().parent.parent)
ASSETS = os.path.join(BASE_DIR, "assets")

# --- COLOR SCHEMES ---
# Each scheme: (cmap_stops, bar_color)
# cmap_stops: list of hex colors from dark/empty → mid → bright/full
# bar_color: single hex used for histogram bars
COLOR_SCHEMES = {
    "green": {
        "cmap": ["#0f1f17", "#1f6f4a", "#5BF69F"],
        "bar":  "#5BF69F",
    },
    "rose": {
        "cmap": ["#1f0f14", "#6f2040", "#F6758A"],
        "bar":  "#F6758A",
    },
    "sky": {
        "cmap": ["#0f1520", "#2a4a7f", "#7EB8F6"],
        "bar":  "#7EB8F6",
    },
    "peach": {
        "cmap": ["#1f1508", "#7f4e1a", "#F6B87E"],
        "bar":  "#F6B87E",
    },
    "lavender": {
        "cmap": ["#130f1f", "#4a2a7f", "#B47EF6"],
        "bar":  "#B47EF6",
    },
    "arctic": {
        "cmap": ["#0a1a1f", "#1a6070", "#6EE8E0"],
        "bar":  "#6EE8E0",
    },
}

def _get_scheme(color_scheme: str) -> dict:
    """Return the scheme dict, falling back to green if unknown."""
    return COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES["green"])


def create_histogram(username, graph_id, path=None):
    if path is None:
        path = os.path.join(ASSETS, "heatmap.png")
    # --- CONFIG ---
    weeks = 20
    days_per_week = 7
    cell_size = 0.32

    # --- FETCH DATA ---
    pixels = get_pixel_dict(username, graph_id)
    if pixels is None:
        return

    # --- DATE RANGE ---
    today = datetime.today().date()
    start_date = today - timedelta(days=weeks * days_per_week - 1)
    all_dates = [start_date + timedelta(days=i) for i in range(weeks * days_per_week)]

    values = np.array(
        [pixels.get(d.strftime("%Y%m%d"), 0) for d in all_dates],
        dtype=float
    )

    max_val = values.max() if values.max() > 0 else 1
    scaled = (values / max_val) * days_per_week

    # --- FIGURE ---
    rows = days_per_week
    cols = weeks
    fig, ax = plt.subplots(figsize=(cols * cell_size, rows * cell_size))
    fig.patch.set_facecolor("#0b0b0b")
    ax.set_facecolor("#0b0b0b")

    x = np.arange(len(scaled))

    # --- SCHEME ---
    scheme = _get_scheme(get_graph_color(username, graph_id))

    # --- BARS ---
    ax.bar(
        x,
        scaled,
        width=0.75,
        color=scheme["bar"],
        alpha=0.95
    )

    # --- WEEK SEPARATORS ---
    for i in range(0, len(scaled), 7):
        ax.axvline(i - 0.5, color="#1c1c1c", linewidth=0.6)

    # --- BASELINE ---
    ax.axhline(0, color="#1f1f1f", linewidth=1)

    # --- LIMITS ---
    ax.set_xlim(-0.5, len(scaled) - 0.5)
    ax.set_ylim(0, rows * 1.05)

    ax.axis("off")
    plt.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)

    os.makedirs(ASSETS, exist_ok=True)
    plt.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)


def create_heatmap(username, graph_id, path=None):
    if path is None:
        path = os.path.join(ASSETS, "heatmap.png")
    # --- CONFIG ---
    weeks = 20
    days_per_week = 7
    cell_size = 0.32          # overall scale
    gap = 0.18                # space between pixels (0.1–0.25 sweet spot)
    radius = 0.28             # rounded corner amount
    gamma = 0.6               # contrast boost (lower = stronger)
    vmin = 0.12               # minimum brightness

    # --- FETCH DATA ---
    pixels = get_pixel_dict(username, graph_id)
    if pixels is None:
        return

    # --- DATE RANGE ---
    today = datetime.today().date()
    start_date = today - timedelta(days=weeks * days_per_week - 1)
    all_dates = [start_date + timedelta(days=i) for i in range(weeks * days_per_week)]

    # --- GRID ---
    grid = np.zeros((days_per_week, weeks), dtype=float)
    future_mask = np.zeros_like(grid, dtype=bool)

    for i, d in enumerate(all_dates):
        w = i // days_per_week
        d_idx = i % days_per_week
        if d > today:
            future_mask[d_idx, w] = True
        else:
            grid[d_idx, w] = pixels.get(d.strftime("%Y%m%d"), 0)

    # --- NORMALIZE ---
    max_val = grid.max() if grid.max() > 0 else 1
    grid_norm = grid / max_val
    masked = np.ma.masked_where((grid_norm == 0) & (~future_mask), grid_norm)

    # --- FIGURE ---
    rows, cols = grid.shape
    fig, ax = plt.subplots(figsize=(cols * cell_size, rows * cell_size))
    fig.patch.set_facecolor("#0b0b0b")
    ax.set_facecolor("#0b0b0b")

    # --- COLORMAP ---
    scheme = _get_scheme(get_graph_color(username, graph_id))
    cmap = LinearSegmentedColormap.from_list("scheme_cmap", scheme["cmap"])

    # --- DRAW PIXELS ---
    pixel_size = 1.0 - gap

    for y in range(rows):
        for x in range(cols):
            val = masked[y, x]

            # skip empty past days
            if np.ma.is_masked(val):
                continue

            if future_mask[y, x]:
                color = "#242424"
                alpha = 0.6
            else:
                val_adj = max(vmin, val) ** gamma
                color = cmap(val_adj)
                alpha = 1.0

            rect = FancyBboxPatch(
                (x + gap / 2, y + gap / 2),
                pixel_size,
                pixel_size,
                boxstyle=f"round,pad=0,rounding_size={radius}",
                linewidth=0,
                facecolor=color,
                alpha=alpha
            )

            ax.add_patch(rect)

    # --- FINAL TOUCHES ---
    ax.set_xlim(0, cols)
    ax.set_ylim(0, rows)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.axis("off")

    plt.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    os.makedirs(ASSETS, exist_ok=True)
    plt.savefig(path, dpi=300, facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    create_heatmap("meaowasaurusthethird", "python")