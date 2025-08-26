import re
import pandas as pd
from typing import Tuple

VALID_DEPARTMENTS = [
    "Creative - Designer", "Creative - Writer",
    "Tech - Front-end", "Tech - Back-end",
    "Video", "Strategy",
    "PR - Traditional", "PR - Social",
]

HOURS_PER_FTE = 32

def extract_dates(df_head: pd.DataFrame) -> list:
    months = df_head.iloc[3, 5:].ffill().tolist()
    days   = df_head.iloc[4, 5:].tolist()
    dates = []
    for m, d in zip(months, days):
        try:
            m_str = str(m)
            if " " in m_str:
                month_name, year = m_str.split()
                dates.append(pd.to_datetime(f"{month_name} {int(float(d))}, {year}"))
            else:
                dates.append(pd.NaT)
        except Exception:
            dates.append(pd.NaT)
    return dates

def parse_workamajig_csv(file_obj) -> Tuple[pd.DataFrame, pd.Timestamp]:
    # Reset to start
    file_obj.seek(0)
    head = pd.read_csv(file_obj, nrows=10)

    start_text = str(head.iloc[0,0])
    m = re.search(r"Start Date:\\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})", start_text)
    report_date = pd.to_datetime(m.group(1)) if m else pd.Timestamp.today().normalize()

    dates = extract_dates(head)

    # Reset again before full read
    file_obj.seek(0)
    df = pd.read_csv(file_obj, skiprows=6)
    df = df.rename(columns={df.columns[1]: "Name"})
    df = df.iloc[:, :5+len(dates)]
    df.columns = list(df.columns[:5]) + dates
    df = df.drop(columns=["Unnamed: 0","Unnamed: 2","Unnamed: 3","Unnamed: 4"], errors="ignore")

    long = df.melt(id_vars=["Name"], var_name="Week", value_name="Hours")
    long["Hours"] = pd.to_numeric(long["Hours"], errors="coerce").fillna(0)
    return long, report_date


def build_weekly_headcount(long_df: pd.DataFrame, employees_df: pd.DataFrame, services_df: pd.DataFrame, report_date: pd.Timestamp):
    emp = employees_df.rename(columns={"Resource Name":"Name"})[["Name","Department"]]
    svc = services_df.rename(columns={"Service":"Name"})[["Name","Department"]]
    mapping = pd.concat([emp, svc], ignore_index=True)

    merged = long_df.merge(mapping, on="Name", how="left")
    merged = merged[merged["Department"].isin(VALID_DEPARTMENTS)]

    merged["Headcount_Demand"] = merged["Hours"] / HOURS_PER_FTE

    weekly = (
        merged.groupby(["Department","Week"], dropna=True)["Headcount_Demand"]
        .sum().reset_index()
    )

    available = (
        employees_df.groupby("Department")["Resource Name"].count()
        .reindex(VALID_DEPARTMENTS).fillna(0).astype(int)
    )

    weekly["Available"] = weekly["Department"].map(available.to_dict())
    weekly["Gap"] = weekly["Available"] - weekly["Headcount_Demand"]

    mask = (weekly["Week"] > report_date) & (weekly["Week"] <= report_date + pd.Timedelta(weeks=12))
    weekly = weekly[mask].copy()

    return weekly, available

def load_definitions(xlsx_file):
    xls = pd.ExcelFile(xlsx_file)
    employees = pd.read_excel(xls, sheet_name="Employees - Resources")
    services  = pd.read_excel(xls, sheet_name="Services")
    return employees, services
