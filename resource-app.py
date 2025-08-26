import io
import datetime
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

st.title("📊 Hart Heat Maps — Cloud Mini App")

# --- Sidebar-CS ---
with st.sidebar:
    st.header("📂 Uploads")

    # Persist definitions file in session state (lasts until app refresh)
    if "defs_file" not in st.session_state:
        st.session_state["defs_file"] = None

    defs_upload = st.file_uploader(
        "📑 Service & Staff Definitions (.xlsx)", type=["xlsx"], key="defs"
    )

    if defs_upload is not None:
        st.session_state["defs_file"] = defs_upload
        st.success("✅ Definitions file uploaded!")

    # Button to clear stored definitions
    if st.button("🧹 Clear Definitions"):
        st.session_state["defs_file"] = None
        st.warning("⚠️ Definitions file cleared. Please upload a new one if needed.")

    active_csv = st.file_uploader("🟢 Active Jobs CSV", type=["csv"], key="active")
    oppty_csv = st.file_uploader("🔵 Oppty Jobs CSV", type=["csv"], key="oppty")

    st.caption("💡 Tip: You only need to upload definitions once per session. Active/Oppty should be updated weekly.")

# --- Layout for charts ---
col1, col2 = st.columns([1, 1], gap="large")

if st.session_state["defs_file"] and active_csv:
    # 1) Load definitions
    employees_df, services_df = load_definitions(st.session_state["defs_file"])

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
    if not st.session_state["defs_file"]:
        st.info("⬆️ Upload the definitions .xlsx (once per session) to get started.")
    else:
        st.info("⬆️ Upload at least the Active CSV to generate the heat maps.")
