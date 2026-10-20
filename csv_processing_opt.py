import csv
import random
import calendar
import gspread
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

# ==========================================
# GLOBALS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
CSV_ROUTE = BASE_DIR / "raw_data.csv"
CLEAN_CSV_PATH = BASE_DIR / "clean_data.csv"
CREDS_PATH = BASE_DIR /"creds.json"
SPREADSHEET_ID = ""

PM_PM_RATES = {'Molino': 15, 'Azure': 25, 'Belgrano': 20, 'Wellhub': 15, 'Rosebud': 30, 'Americano Health': 10, 'Gecko': 10, 'Panorama': 12, 'First Aid': 26}
COMMISSION_AGENT_RATE = 0.45
COMMISSION_AGENCY_RATE = 0.55

PREMIUM_RANGES = {
    ("Bronze", 1): (0, 25), ("Bronze", 2): (25, 75), ("Bronze", 3): (75, 125), ("Bronze", 4): (125, 175),
    ("Silver", 1): (50, 100), ("Silver", 2): (100, 200), ("Silver", 3): (200, 300), ("Silver", 4): (300, 400),
    ("Gold", 1): (150, 200), ("Gold", 2): (200, 350), ("Gold", 3): (350, 500), ("Gold", 4): (500, 650)
}

# ==========================================
# DATA CLEANING UTILITIES
# ==========================================

def clean_dates(series:pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.replace(r'[/.,]', '-', regex=True)
    s = s.str.extract(r'(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}-\d{1,2}-\d{4})')[0]
    parsed = pd.to_datetime(s, format='%m-%d-%Y', errors='coerce')
    parsed_alt = pd.to_datetime(s, format='%Y-%m-%d', errors='coerce')
    result = parsed.fillna(parsed_alt)
    invalid_year = result.dt.year < 2026
    result.loc[invalid_year] = result.loc[invalid_year].map(lambda d: d.replace(year=2026) if pd.notna(d) else d)
    return result

def impute_missing_premium(row):
    key = (row['metal_tier'], row['members_covered'])
    if key in PREMIUM_RANGES:
        low, high = PREMIUM_RANGES[key]
        return round(np.random.uniform(low, high), 2)
    return round(np.random.uniform(0,500), 2)

# ==========================================
# PIPELINE ETL
# ==========================================

def run_etl():
    df = pd.read_csv(CSV_ROUTE)

    # DUPLICATES
    df["missing_count"] = df.isna().sum(axis=1)
    df = df.sort_values(by="missing_count").drop_duplicates(subset="policy_id", keep="first").drop(columns=['missing_count'])
    
    # ID
    df["policy_id"] = df["policy_id"].astype(str).str.strip().str.upper().str.replace(" ", "")
    short_mask = df["policy_id"].str.len() == 5
    df.loc[short_mask, "policy_id"] = df.loc[short_mask, "policy_id"].str[:2] + "-" + df.loc[short_mask, "policy_id"].str[2:]
    long_mask = df["policy_id"].str.len() > 6
    df.loc[long_mask, "policy_id"] = df.loc[long_mask, "policy_id"].str.slice(0,6)

    # NAMES AND AGENTS
    for col in ["client_name", "agent"]:
        df[col] = df[col].astype(str).str.strip().str.title().str.replace("-", " ", regex=False)
        comma_mask = df[col].str.contains(",", na=False)
        split_names =  df.loc[comma_mask, col].str.split(",", expand=True)
        if not split_names.empty and split_names.shape[1] == 2:
            df.loc[comma_mask, col] = split_names[1].str.strip() + " " + split_names[0].str.strip()

    # STATUS
    status_clean = df["status"].astype(str).str.strip().str.lower()
    df["status"] = np.select([status_clean.str.startswith('act'), status_clean.str.startswith('ter'), status_clean.str.startswith('pip')],
                             ["Active", "Terminated", "Pipeline"], default="Active")

    # MEMBERS
    num_map = {"one": 1, "two": 2, "three": 3, "four": 4}
    df["members_covered"] = df["members_covered"].replace(num_map)
    df["members_covered"] = pd.to_numeric(df["members_covered"], errors="coerce").fillna(1)
    df.loc[~df["members_covered"].between(1,4), "members_covered"] = 1
    df["members_covered"] = df["members_covered"].astype(int)

    # PREMIUM
    df["premium"] = df["premium"].astype(str).str.strip().str.replace(",", ".", regex=False).str.replace("-", "", regex=False)
    df["premium"] = df["premium"].str.extract(r"(\d+\.?\d*)")[0]
    df["premium"] = pd.to_numeric(df["premium"], errors="coerce")
    df.loc[df["premium"] > 650, "premium"] = np.nan
    missing_premium = df["premium"].isna()
    df.loc[missing_premium, "premium"] = df.loc[missing_premium].apply(impute_missing_premium, axis=1)

    # CLEANING DATES
    df["purchase_date"] = clean_dates(df["purchase_date"])
    df["cancel_date"] = clean_dates(df["cancel_date"])
    df["pipeline_deadline"] = clean_dates(df["pipeline_deadline"])

    # MISSING DATES
    df.loc[df["status"] != "Pipeline", "pipeline_deadline"] = pd.NaT
    pipeline_date_missing = (df["status"] == "Pipeline") & (df["pipeline_deadline"].isna())
    df.loc[pipeline_date_missing, "pipeline_deadline"] = df.loc[pipeline_date_missing, "purchase_date"] + pd.Timedelta(days=75)

    purchase_date_missing = df["purchase_date"].isna()
    df.loc[purchase_date_missing & (df["status"] == "Active"), "purchase_date"] = pd.Timestamp("2026-01-01")
    df.loc[purchase_date_missing & (df["status"] == "Terminated"), "purchase_date"] = pd.Timestamp("2026-01-01")
    df.loc[purchase_date_missing & (df["status"] == "Pipeline"), "purchase_date"] = (df.loc[purchase_date_missing & (df["status"] == "Pipeline"), "pipeline_deadline"] - pd.Timedelta(days=75))

    df.loc[df["status"] != "Terminated", "cancel_date"] = pd.NaT
    missing_cancel_date = (df["status"] == "Terminated") & (df["cancel_date"].isna())
    df.loc[missing_cancel_date, "cancel_date"] = df.loc[missing_cancel_date, "purchase_date"] + pd.offsets.MonthEnd(1)

    #EXPIRATION DATES
    limit_date = pd.Timestamp("2026-06-30")
    expired_mask = (df["status"] == "Pipeline") & (df["pipeline_deadline"] < limit_date)
    df.loc[expired_mask, "status"] = "Pipeline Expired"
    df.loc[expired_mask, "cancel_date"] = df.loc[expired_mask, "pipeline_deadline"] + pd.offsets.MonthEnd(0)

    #PIPELINE REASON
    reason_cleaned = df["pipeline_reason"].astype(str).str.strip().str.lower()
    df["pipeline_reason"] = np.select([reason_cleaned.str.contains("document", na=False), reason_cleaned.str.contains("payment", na=False)], ["Missing Documents", "Missing Payment"], default="")
    df.loc[(df["status"] == "Pipeline") & (df["pipeline_reason"].eq("")), "pipeline_reason"] = "Missing Payment"
    df.loc[df["status"] != "Pipeline", "pipeline_reason"] = np.nan

    #CALCULATE COMMISSIONS WITH PER MEMBER PER MONTH RATES AND CARRIER
    df["pm_pm"] = df["carrier"].map(PM_PM_RATES).fillna(0)
    df["commission_total"] = df["pm_pm"] * df["members_covered"]
    df["agent_commission"] = (df["commission_total"] * COMMISSION_AGENT_RATE).round(2)
    df["agency_commission"] = (df["commission_total"] * COMMISSION_AGENCY_RATE).round(2)

    #MONTHLY COMMISSIONS BREAKDOWN AND PIVOT
    months = pd.date_range(start="2026-01-01", end="2026-06-01", freq="MS")
    record_list = []

    for m in months:
        month_end = m + pd.offsets.MonthEnd(0)
        active_in_month = (df["purchase_date"] <= m) & (df["cancel_date"].isna() | (df["cancel_date"] >= month_end))
        df_month = df[active_in_month].copy()
        df_month["month"] = m
        record_list.append(df_month)

    df_monthly = pd.concat(record_list, ignore_index=True) if record_list else pd.DataFrame()
    agents_pivot = pd.pivot_table(df_monthly, index="month", columns="agent", values="agent_commission", aggfunc="sum", fill_value=0)
    
    agency_sum = df_monthly.groupby("month")["agency_commission"].sum()
    agents_pivot.insert(0, "Agency", agency_sum)
    agents_pivot.insert(1, "Agents", agents_pivot.drop(columns=["Agency"]).sum(axis=1))
    agents_pivot = agents_pivot.reset_index()
    agents_pivot["month"] = agents_pivot["month"].dt.strftime("%m-%d-%Y")

    #FORMAT DATES
    date_fields = ["purchase_date", "cancel_date", "pipeline_deadline"]
    for field in date_fields:
        df[field] = df[field].dt.strftime("%m-%d-%Y").fillna("")

    #SORT DF
    df = df.fillna("").sort_values("policy_id").reset_index(drop=True)

    print(f"✅✅✅\nData Processed\n{"*" * 25}")
    return df, agents_pivot

# ==========================================
# SHEETS UPLOADING
# ==========================================

def upload_to_sheets(df: pd.DataFrame, pivot_agents: pd.DataFrame):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    ss = client.open_by_key(SPREADSHEET_ID)

    #FOR DATA TAB
    data_matrix = [df.columns.to_list()] + df.values.tolist()
    try:
        worksheet = ss.worksheet("DATA")
    except WorksheetNotFound:
        worksheet =  ss.add_worksheet(title="DATA 1", rows=len(data_matrix), cols=len(df.columns))

    if (worksheet.row_count != len(data_matrix) or worksheet.col_count != len(df.columns)):
        worksheet.resize(rows=len(data_matrix), cols=len(df.columns))

    worksheet.clear()

    worksheet.update(range_name="A1", values=data_matrix)

    #FOR CALCULATIONS TAB
    calc_matrix = [pivot_agents.columns.tolist()] + pivot_agents.values.tolist()
    try:
        worksheet_calc = ss.worksheet("CALCULATIONS")
        worksheet_calc.batch_clear(['A2:K10'])
    except WorksheetNotFound:
        worksheet_calc = ss.add_worksheet(title="CALCULATIONS", rows=len(calc_matrix) + 5, cols=len(pivot_agents.columns))

    worksheet_calc.update(range_name="A2", values=[["MONTHLY COMMISSIONS CALCULATIONS USING PANDAS"]])
    worksheet_calc.update(range_name="A4", values=calc_matrix)

    last_row = 4 + len(calc_matrix)
    last_col = chr(64 + len(pivot_agents.columns))
    worksheet_calc.format(f'B5:{last_col}{last_row}', {'numberFormat': {'type': 'CURRENCY', 'pattern': '$#,##0.00'}})

    print(f"✅✅✅\nData Uploaded\n{"*" * 25}")

def main():
    df, pivot = run_etl()
    upload_to_sheets(df, pivot)
    df.to_csv(CLEAN_CSV_PATH, index=False)

if __name__ == "__main__":
    main()