import io
import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from parsing import (
    load_definitions,
    parse_workamajig_csv,
    build_weekly_headcount,
)
from charts import make_heatmap_figure

st.set_page_config(page_title="Hart Heat Maps", layout="wide")

st.title("📊 Hart Staffing Heat Map")

# --- Persistent storage for definitions file ---
DATA_DIR = Path("hart_app/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFS_PATH = DATA_DIR / "Service-Staff-Definitions.xlsx"

# --- Sidebar ---
with st.sidebar:
    st.header("📂 Uploads")

    # Definitions uploader
    st.subheader("Definitions")
    defs_uploader = st.file_uploader("Service-Staff-Definitions.xlsx", type=["xlsx"], key="defs")
    if defs_uploader:
        with open(DEFS_PATH, "wb") as f:
            f.write(defs_uploader.read())

    # Workload CSV uploader
    st.subheader("Workload CSV")
    st.caption("Single CSV in the same structure as before.")
    active_csv = st.file_uploader("Upload CSV", type=["csv"], key="workload")


# --- Main App ---

def make_pdf_legend(available):
    import matplotlib.pyplot as plt

    groups = {
        "Account": ["Account"],
        "Creative": ["Creative - Designer", "Creative - Writer"],
        "PR": ["PR - Traditional", "PR - Social"],
        "Project Management": ["Project Management"],
        "Strategy": ["Strategy"],
        "Tech": ["Tech - Front-end", "Tech - Back-end"],
        "Video": ["Video"],
    }

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.axis("off")

    ax.text(0.5, 0.95, "Current Staff Availability",
            ha="center", va="top", fontsize=16, fontweight="bold")

    positions = [
        (0, 1), (1, 1), (2, 1), (3, 1),
        (0, 0), (1, 0), (2, 0)
    ]
    cell_w, cell_h = 0.22, 0.35

    for (dept, subs), (col, row) in zip(groups.items(), positions):
        x0, y0 = 0.05 + col * cell_w, 0.1 + row * cell_h
        ax.add_patch(plt.Rectangle((x0, y0), cell_w, cell_h,
                                   fill=False, lw=1.2, color="black",
                                   transform=ax.transAxes))
        ax.text(x0 + cell_w/2, y0 + cell_h - 0.05, dept,
                ha="center", va="top", fontsize=12, fontweight="bold",
                transform=ax.transAxes)

        lines = [f"{d}: {int(available.get(d, 0))}" for d in subs]
        total = int(sum(available.get(d, 0) for d in subs))
        lines.append(f"Total: {total}")
        for i, line in enumerate(lines):
            ax.text(x0 + cell_w/2, y0 + cell_h - 0.15 - i*0.08, line,
                    ha="center", va="top", fontsize=10,
                    transform=ax.transAxes)

    fig.tight_layout()
    return fig



def render_legend_html(available):
    groups = {
        "Account 🧾": ["Account"],
        "Creative 🎨": ["Creative - Designer", "Creative - Writer"],
        "PR 📢": ["PR - Traditional", "PR - Social"],
        "Project Management 📋": ["Project Management"],
        "Strategy 🧭": ["Strategy"],
        "Tech 💻": ["Tech - Front-end", "Tech - Back-end"],
        "Video 🎥": ["Video"],
    }

    rows = []
    for dept, subs in groups.items():
        lines = [f"{d}: {int(available.get(d, 0))}" for d in subs]
        total = int(sum(available.get(d, 0) for d in subs))
        emoji_icon = dept.split()[-1]
        dept_name = " ".join(dept.split()[:-1])
        html = f"""
        <div style='text-align:center; font-family:sans-serif;'>
            <span style='font-size:28px;'>{emoji_icon}</span><br>
            <b>{dept_name}</b><br>
            {'<br>'.join(lines)}<br>
            <b>Total: {total}</b>
        </div>
        """
        rows.append(html)

    table_html = f"""
    <h3 style='text-align:center;'>Current Staff Availability</h3>
    <table style='margin:auto; border-collapse:collapse; font-family:sans-serif;'>
      <tr>
        {''.join(f'<td style="border:1px solid black; padding:10px; vertical-align:top;">{cell}</td>' for cell in rows[:4])}
      </tr>
      <tr>
        {''.join(f'<td style="border:1px solid black; padding:10px; vertical-align:top;">{cell}</td>' for cell in rows[4:])}
      </tr>
    </table>
    """
    return table_html


if DEFS_PATH.exists() and active_csv:
    # 1) Load definitions from persistent file
    employees_df, services_df = load_definitions(DEFS_PATH)

    # 2) Parse single CSV
    active_long, report_date_active = parse_workamajig_csv(active_csv)

    # 3) Weekly headcounts (two windows: 13 and 26 weeks)
    weekly_13, available = build_weekly_headcount(
        active_long, employees_df, services_df, report_date_active, window_weeks=13
    )
    weekly_26, _ = build_weekly_headcount(
        active_long, employees_df, services_df, report_date_active, window_weeks=26
    )

    # 4) Figures
    col1, col2 = st.columns([1, 1], gap="large")

    fig_13 = make_heatmap_figure(
        weekly_13,
        available,
        title="Hart Heat Map — 13 Weeks",
    )
    with col1:
        st.pyplot(fig_13, use_container_width=True)

    fig_26 = make_heatmap_figure(
        weekly_26,
        available,
        title="Hart Heat Map — 26 Weeks",
    )
    with col2:
        st.pyplot(fig_26, use_container_width=True)

    # 4b) Current staff availability legend
    st.subheader("Current Staff Availability")
    st.markdown(render_legend_html(available), unsafe_allow_html=True)


    # 5) PDF export with both heat maps
    buf = io.BytesIO()
    today = datetime.date.today().strftime("%Y-%m-%d")
    with PdfPages(buf) as pdf:
        pdf.savefig(fig_13)
        pdf.savefig(fig_26)
        pdf.savefig(make_pdf_legend(available))
    buf.seek(0)

    st.download_button(
        "⬇️ Download PDF Report",
        data=buf,
        file_name=f"hart-heat-maps-{today}.pdf",
        mime="application/pdf",
    )

else:
    st.info("⬆️ Upload the definitions file and a single workload CSV to generate the heat maps.")
