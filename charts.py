# charts.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import TwoSlopeNorm
import matplotlib.patheffects as pe

NAVY = "#182735"
RED  = "#b1483f"

# Red -> White -> Navy map
_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "HartMap",
    [mcolors.to_rgb(RED), (1, 1, 1), mcolors.to_rgb(NAVY)],
    N=256
)

def _pivot(weekly: pd.DataFrame, value="Gap") -> pd.DataFrame:
    p = weekly.pivot(index="Department", columns="Week", values=value)
    # Format column labels as MM/DD/YYYY (no timestamps)
    p.columns = [pd.to_datetime(c).strftime("%m/%d/%Y") for c in p.columns]
    return p

def _luminance(rgb):
    """Perceived luminance for text color decision (rgb in 0..1)."""
    r, g, b = rgb[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def make_heatmap_figure(
    weekly: pd.DataFrame,
    available,
    title: str,
    dept_order=None,
    annotate_fmt="{:.1f}",
):
    pivot = _pivot(weekly, "Gap")
    if dept_order is not None:
        pivot = pivot.reindex(dept_order)

    data = pivot.values.astype(float)
    # Handle empty or all-NaN cases gracefully
    if data.size == 0 or np.all(~np.isfinite(data)):
        fig, ax = plt.subplots(figsize=(11, 6))
        ax.text(0.5, 0.5, "No data for selected period", ha="center", va="center")
        ax.axis("off")
        return fig

    # Color normalization centered at 0
    finite_vals = data[np.isfinite(data)]
    vmin = float(np.min(finite_vals)) if finite_vals.size else -5.0
    vmax = float(np.max(finite_vals)) if finite_vals.size else 5.0
    # Ensure both sides exist so TwoSlopeNorm works nicely
    if vmin >= 0: vmin = -1.0
    if vmax <= 0: vmax =  1.0
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax)

    fig, ax = plt.subplots(figsize=(11, 6))
    im = ax.imshow(data, cmap=_CMAP, norm=norm, aspect="auto")

    # Force the balanced band (-0.9..0.9) to white background
    rows, cols = data.shape
    for i in range(rows):
        for j in range(cols):
            val = data[i, j]
            if np.isfinite(val) and (-0.9 <= val <= 0.9):
                ax.add_patch(
                    plt.Rectangle(
                        (j - 0.5, i - 0.5),
                        1, 1,
                        facecolor="white",
                        edgecolor="lightgray",
                        lw=0.6
                    )
                )

    # Axes ticks/labels
    ax.set_xticks(np.arange(cols))
    ax.set_yticks(np.arange(rows))
    ax.set_xticklabels(list(pivot.columns), rotation=45, ha="right")
    ax.set_yticklabels(list(pivot.index))

    # Annotations with automatic contrast
    for i in range(rows):
        for j in range(cols):
            val = data[i, j]
            if not np.isfinite(val):
                continue

            # Default text color is black; switch to white if background is dark
            if -0.9 <= val <= 0.9:
                # Balanced band: white background → black text
                text_color = "black"
            else:
                rgba = _CMAP(norm(val))
                text_color = "white" if _luminance(rgba) < 0.5 else "black"

            ax.text(
                j, i, annotate_fmt.format(val),
                ha="center", va="center",
                fontsize=8, color=text_color,
                path_effects=[pe.withStroke(linewidth=1.0, foreground="black" if text_color=="white" else "white")]
            )

    ax.set_title(title)
    ax.set_xlabel("Week Starting")
    ax.set_ylabel("Department")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Headcount Gap")

    fig.tight_layout()
    return fig



def legend_box(available_series: pd.Series):
    """Legend with PNG icons, centered text, bold totals, row-equalized cell heights."""
    from matplotlib.patches import Rectangle
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
    import matplotlib.image as mpimg

    groups = {
        "Account": ["Account"],
        "Creative": ["Creative - Designer", "Creative - Writer"],
        "PR": ["PR - Traditional", "PR - Social"],
        "Project Management": ["Project Management"],
        "Strategy": ["Strategy"],
        "Tech": ["Tech - Front-end", "Tech - Back-end"],
        "Video": ["Video"],
    }

    icons = {
        "Account": "icons/account.png",
        "Creative": "icons/creative.png",
        "PR": "icons/pr.png",
        "Project Management": "icons/project.png",
        "Strategy": "icons/strategy.png",
        "Tech": "icons/tech.png",
        "Video": "icons/video.png",
    }

    def make_lines(subs):
        lines = [f"{d}: {int(available_series.get(d, 0))}" for d in subs]
        total = int(sum(available_series.get(d, 0) for d in subs))
        lines.append(f"Total: {total}")
        return lines

    headers = list(groups.keys())
    data = {h: make_lines(subs) for h, subs in groups.items()}

    positions = [
        (0, 1), (1, 1), (2, 1), (3, 1),
        (0, 0), (1, 0), (2, 0)
    ]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis("off")

    # Title
    ax.text(
        0.5, 1.05, "Current Staff Availability",
        ha="center", va="bottom", fontsize=14, fontweight="bold",
        family="DejaVu Sans", transform=ax.transAxes
    )

    cell_w = 0.22

    # --- Compute tallest cell per row ---
    row_heights = {0: 0, 1: 0}
    for (dept, lines), (col, row) in zip(data.items(), positions):
        n_text_lines = len(lines) + 1  # dept name + text lines
        n_icon_lines = 2
        total_lines = n_text_lines + n_icon_lines
        cell_h = 0.05 * total_lines
        if cell_h > row_heights[row]:
            row_heights[row] = cell_h

    for (dept, lines), (col, row) in zip(data.items(), positions):
        cell_h = row_heights[row]  # equalized height per row
        y0 = 0.1 + row * 0.4
        x0 = 0.05 + col * cell_w

        ax.add_patch(
            Rectangle((x0, y0), cell_w, cell_h,
                      fill=False, lw=1.2, color="black",
                      transform=ax.transAxes)
        )

        # Icon
        if dept in icons:
            try:
                img = mpimg.imread(icons[dept])
                imagebox = OffsetImage(img, zoom=0.1)
                ab = AnnotationBbox(
                    imagebox, (x0 + cell_w/2, y0 + cell_h - 0.05),
                    frameon=False, box_alignment=(0.5, 1), xycoords=ax.transAxes
                )
                ax.add_artist(ab)
            except FileNotFoundError:
                pass

        # Department name
        ax.text(
            x0 + cell_w/2, y0 + cell_h - 0.18, dept,
            ha="center", va="top", fontsize=11, fontweight="bold",
            family="DejaVu Sans", transform=ax.transAxes
        )

        # Lines
        for i, line in enumerate(lines):
            weight = "bold" if line.startswith("Total") else "normal"
            ax.text(
                x0 + cell_w/2, y0 + cell_h - 0.28 - i*0.07, line,
                ha="center", va="top", fontsize=10, fontweight=weight,
                family="DejaVu Sans", transform=ax.transAxes
            )

    fig.tight_layout()
    return fig
