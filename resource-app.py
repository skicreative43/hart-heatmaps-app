import io
import os
import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from parsing import (
    load_definitions,
    parse_workamajig_csv,
    build_weekly_headcount,
    VALID_DEPARTMENTS,
)
from charts import make_heatmap_figure, legend_box

st.set_page_config(page_title="Hart Heat Maps", layout="wide")

st.title("📊 Hart Staffing Heat Map")

# --- Persistent storage for definitions file ---
DATA_DIR = Path("hart_app/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFS_PATH = DATA_DIR / "Service-Staff-Definitions.xlsx"

# --- Sidebar ---
with st.sidebar:
    st.header("📂 Uploads")

    defs_upload = st.file_uploader(
        "📑 Service & Staff Definitions (.xlsx)", type=["xlsx"], key="defs"
    )

    if defs_upload is not None:
        # Save uploaded file to disk so it persists
        with open(DEFS_PATH, "wb") as f:
            f.write(defs_upload.getbuffer())
        st.success("✅ Definitions file uploaded and saved!")

    # Button to clear stored definitions
    if st.button("🧹 Clear Definitions"):
        if DEFS_PATH.exists():
            DEFS_PATH.unlink()
        st.warning("⚠️ Definitions file cleared.")

    active_csv = st.file_uploader("🟢 Active Jobs CSV", type=["csv"], key="active")
    oppty_csv = st.file_uploader("🔵 Oppty Jobs CSV", type=["csv"], key="oppty")

    st.caption("💡 Tip: You only need to upload definitions once. Active/Oppty should be updated weekly.")

# --- Layout for charts ---
col1, col2 = st.columns([1, 1], gap="large")

if DEFS_PATH.exists() and active_csv:
    # 1) Load definitions from persistent file
    employees_df, services_df = load_definitions(DEFS_PATH)

    # 2) Parse CSVs
    active_long, report_date_active = parse_workamajig_csv(active_csv)
    oppty_long, report_date_oppty = (
        parse_workamajig_csv(oppty_csv) if oppty_csv else (pd.DataFrame(), report_date_active)
    )

    # 3) Weekly headcounts
    weekly_active, available = build_weekly_headcount(
        active_long, employees_df, services_df, report_date_active
    )
    weekly_combined, _ = build_weekly_headcount(
        pd.concat([active_long, oppty_long], ignore_index=True),
        employees_df,
        services_df,
        report_date_active,
    )

    # 4) Figures (Active, Combined)
    fig_active = make_heatmap_figure(
        weekly_active,
        available,
        title="🟢 Hart Heat Map — Active Jobs Only",
        dept_order=[
            "Creative - Designer",
            "Creative - Writer",
            "PR - Traditional",
            "PR - Social",
            "Strategy",
            "Tech - Front-end",
            "Tech - Back-end",
            "Video",
        ],
        annotate_fmt="{:.1f}",
    )

    fig_combined = make_heatmap_figure(
        weekly_combined,
        available,
        title="🔵 Hart Heat Map — Active + Oppty Combined",
        dept_order=[
            "Creative - Designer",
            "Creative - Writer",
            "PR - Traditional",
            "PR - Social",
            "Strategy",
            "Tech - Front-end",
            "Tech - Back-end",
            "Video",
        ],
        annotate_fmt="{:.1f}",
    )

    # Render charts
    with col1:
        st.pyplot(fig_active, clear_figure=False)
    with col2:
        st.pyplot(fig_combined, clear_figure=False)

    # Legend below charts
    st.markdown("---")
    st.subheader("👥 Current Staff Availability")
    legend_fig = legend_box(available)
    st.pyplot(legend_fig, clear_figure=False)

    # --- Direct PDF export ---
    today = datetime.date.today().strftime("%Y-%m-%d")

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        pdf.savefig(fig_active)
        pdf.savefig(fig_combined)
        pdf.savefig(legend_fig)
    buf.seek(0)

    st.download_button(
        label="📥 Download PDF Report",
        data=buf,
        file_name=f"hart_heatmaps_report_{today}.pdf",
        mime="application/pdf",
    )

else:
    if not DEFS_PATH.exists():
        st.info("⬆️ Upload the definitions .xlsx (once) to get started. It will be remembered for future sessions.")
    else:
        st.info("⬆️ Upload at least the Active CSV to generate the heat maps.")
