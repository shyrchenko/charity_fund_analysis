from pathlib import Path
import sys

import streamlit as st
import plotly.express as px
import pandas as pd
import duckdb

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from db.utils import get_monthly_report

con = duckdb.connect("charity_reports.duckdb")

st.set_page_config(page_title="Charity Donations Analytics", layout="wide")
st.title("Charity Donations Analytics")

df = get_monthly_report(con)
df["month"] = pd.to_datetime(df["month"])
funds = df["fund_name"].unique().tolist()
min_month = df["month"].min().to_pydatetime()
max_month = df["month"].max().to_pydatetime()

# ---- filters ----

st.sidebar.header("Filters")

selected_funds = st.sidebar.multiselect(
    "Select Funds",
    options=funds,
    default=funds
)
date_slider = st.sidebar.slider(
    "Select Date Range",
    min_value=min_month,
    max_value=max_month,
    value=(min_month, max_month),
    format="YYYY-MM"
)


df = df[df["fund_name"].isin(selected_funds)]
df = df[(df["month"] >= date_slider[0]) & (df["month"] <= date_slider[1])]

OUTLIERS_WIDGET_KEY = "outliers_filter"
outliers_checkbox = st.sidebar.checkbox("Show Outliers Filter", value=False)
if outliers_checkbox:
    selection_keys = (
        df["fund_name"] + " - " + df["month"].dt.strftime("%Y-%m")
    )
    all_keys = selection_keys.unique().tolist()

    existing_outliers = st.session_state.get(OUTLIERS_WIDGET_KEY, [])
    valid_outliers = [item for item in existing_outliers if item in all_keys]
    if existing_outliers != valid_outliers:
        st.session_state[OUTLIERS_WIDGET_KEY] = valid_outliers

    outliers = st.sidebar.multiselect(
        "Select Outliers to Exclude",
        options=all_keys,
        default=valid_outliers,
        key=OUTLIERS_WIDGET_KEY
    )
    df = df[~selection_keys.isin(outliers)]
else:
    st.session_state.pop(OUTLIERS_WIDGET_KEY, None)


# ---- KPIs ----
st.subheader("Key Metrics")

col1,col2 = st.columns(2)

col1.metric("Total Amount, UAH", round(df["total_amount"].sum(), 2))

median_month_income = df.groupby("month")["total_amount"].sum().median()
col2.metric("Median Month Income, UAH", round(median_month_income, 2))

st.subheader("Monthly Donations")

df["month_str"] = df["month"].dt.strftime("%Y-%m")

fig = px.bar(
    df,
    x="month_str",
    y="total_amount",
    color="fund_name",
    barmode="group"
)

st.plotly_chart(fig, width="stretch")
