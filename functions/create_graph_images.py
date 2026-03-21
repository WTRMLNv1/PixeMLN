# functions/create_graph_images.py
# Save a heatmap or histogram chart of pixel data
# -----------------------------------------------------------------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
    _project_root = Path(__file__).resolve().parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))
    from helpers.json_manager import get_pixel_dict, get_graph_color

from helpers.logger import get_logger

log = get_logger(__name__)

BASE_DIR = str(Path(__file__).resolve().parent.parent)
ASSETS   = os.path.join(BASE_DIR, "assets")

# --- COLOR SCHEMES ---
COLOR_SCHEMES = {
    "green":    {"cmap": ["#0f1f17", "#1f6f4a", "#5BF69F"], "bar": "#5BF69F"},
    "rose":     {"cmap": ["#1f0f14", "#6f2040", "#F6758A"], "bar": "#F6758A"},
    "sky":      {"cmap": ["#0f1520", "#2a4a7f", "#7EB8F6"], "bar": "#7EB8F6"},
    "peach":    {"cmap": ["#1f1508", "#7f4e1a", "#F6B87E"], "bar": "#F6B87E"},
    "lavender": {"cmap": ["#130f1f", "#4a2a7f", "#B47EF6"], "bar": "#B47EF6"},
    "arctic":   {"cmap": ["#0a1a1f", "#1a6070", "#6EE8E0"], "bar": "#6EE8E0"},
}

def _get_scheme(color_scheme: str) -> dict:
    return COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES["green"])


def create_histogram(username, graph_id, path=None):
    if path is None:
        path = os.path.join(ASSETS, "heatmap.png")

    log.debug("Rendering histogram for %s/%s → %s", username, graph_id, path)

    weeks        = 20
    days_per_week = 7
    cell_size    = 0.32

    pixels = get_pixel_dict(username, graph_id)
    if pixels is None:
        log.warning("create_histogram: no pixel data for %s/%s", username, graph_id)
        return

    today      = datetime.today().date()
    start_date = today - timedelta(days=weeks * days_per_week - 1)
    all_dates  = [start_date + timedelta(days=i) for i in range(weeks * days_per_week)]

    values = np.array(
        [pixels.get(d.strftime("%Y%m%d"), 0) for d in all_dates],
        dtype=float
    )

    max_val = values.max() if values.max() > 0 else 1
    scaled  = (values / max_val) * days_per_week

    rows, cols = days_per_week, weeks
    fig, ax = plt.subplots(figsize=(cols * cell_size, rows * cell_size))
    fig.patch.set_facecolor("#0b0b0b")
    ax.set_facecolor("#0b0b0b")

    x      = np.arange(len(scaled))
    scheme = _get_scheme(get_graph_color(username, graph_id))

    ax.bar(x, scaled, width=0.75, color=scheme["bar"], alpha=0.95)

    for i in range(0, len(scaled), 7):
        ax.axvline(i - 0.5, color="#1c1c1c", linewidth=0.6)
    ax.axhline(0, color="#1f1f1f", linewidth=1)

    ax.set_xlim(-0.5, len(scaled) - 0.5)
    ax.set_ylim(0, rows * 1.05)
    ax.axis("off")
    plt.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)

    os.makedirs(ASSETS, exist_ok=True)
    plt.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    log.info("Histogram saved: %s/%s → %s", username, graph_id, path)


def create_heatmap(username, graph_id, path=None):
    if path is None:
        path = os.path.join(ASSETS, "heatmap.png")

    log.debug("Rendering heatmap for %s/%s → %s", username, graph_id, path)

    weeks         = 20
    days_per_week = 7
    cell_size     = 0.32
    gap           = 0.18
    radius        = 0.28
    gamma         = 0.6
    vmin          = 0.12

    pixels = get_pixel_dict(username, graph_id)
    if pixels is None:
        log.warning("create_heatmap: no pixel data for %s/%s", username, graph_id)
        return

    today      = datetime.today().date()
    start_date = today - timedelta(days=weeks * days_per_week - 1)
    all_dates  = [start_date + timedelta(days=i) for i in range(weeks * days_per_week)]

    grid        = np.zeros((days_per_week, weeks), dtype=float)
    future_mask = np.zeros_like(grid, dtype=bool)

    for i, d in enumerate(all_dates):
        w     = i // days_per_week
        d_idx = i % days_per_week
        if d > today:
            future_mask[d_idx, w] = True
        else:
            grid[d_idx, w] = pixels.get(d.strftime("%Y%m%d"), 0)

    max_val   = grid.max() if grid.max() > 0 else 1
    grid_norm = grid / max_val
    masked    = np.ma.masked_where((grid_norm == 0) & (~future_mask), grid_norm)

    rows, cols = grid.shape
    fig, ax    = plt.subplots(figsize=(cols * cell_size, rows * cell_size))
    fig.patch.set_facecolor("#0b0b0b")
    ax.set_facecolor("#0b0b0b")

    scheme = _get_scheme(get_graph_color(username, graph_id))
    cmap   = LinearSegmentedColormap.from_list("scheme_cmap", scheme["cmap"])

    pixel_size = 1.0 - gap

    for y in range(rows):
        for x in range(cols):
            val = masked[y, x]
            if np.ma.is_masked(val):
                continue
            if future_mask[y, x]:
                color = "#242424"
                alpha = 0.6
            else:
                val_adj = max(vmin, val) ** gamma
                color   = cmap(val_adj)
                alpha   = 1.0

            rect = FancyBboxPatch(
                (x + gap / 2, y + gap / 2),
                pixel_size, pixel_size,
                boxstyle=f"round,pad=0,rounding_size={radius}",
                linewidth=0,
                facecolor=color,
                alpha=alpha,
            )
            ax.add_patch(rect)

    ax.set_xlim(0, cols)
    ax.set_ylim(0, rows)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.axis("off")

    plt.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    os.makedirs(ASSETS, exist_ok=True)
    plt.savefig(path, dpi=300, facecolor=fig.get_facecolor())
    plt.close(fig)
    log.info("Heatmap saved: %s/%s → %s", username, graph_id, path)


if __name__ == "__main__":
    create_heatmap("meaowasaurusthethird", "python")
