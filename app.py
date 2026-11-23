"""NHS Wales Emergency Department Performance dashboard.
Run with: streamlit run app.py
"""
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

HERE = Path(__file__).parent
TIDY = HERE / "data" / "processed" / "ed_performance_tidy.csv"
DQ = HERE / "data" / "processed" / "data_quality_log.csv"

st.set_page_config(page_title="NHS Wales ED Performance", layout="wide")

@st.cache_data(ttl=24 * 3600, show_spinner="Loading the latest StatsWales data...")
def load():
    # Use the notebook's output if it exists, otherwise rebuild from StatsWales
    if TIDY.exists():
        df = pd.read_csv(TIDY, parse_dates=["month"])
        dq = pd.read_csv(DQ) if DQ.exists() else pd.DataFrame()
        return df, dq
    from ed_pipeline import download_raw, clean
    return clean(download_raw())


df, dq = load()
latest = df["month"].max()

# Boards with no major ED (e.g. Powys) are not comparable, so keep them out of rankings
board_types = df[df.level == "Health board"].groupby("area")["unit_type"].unique()
no_major = [b for b, t in board_types.items() if "Major" not in t]
current_boards = sorted(df[(df.level == "Health board") & (df.month == latest)]["area"].unique())

# ---------- Sidebar ----------
st.sidebar.header("Filters")
area = st.sidebar.selectbox("Area", ["Wales"] + current_boards)
unit_label = {"All": "All emergency care facilities", "Major": "Major EDs only", "Minor": "Minor injury units only"}
available = [u for u in ["All", "Major", "Minor"] if ((df.area == area) & (df.unit_type == u)).any()]
unit = st.sidebar.selectbox("Unit type", available, format_func=unit_label.get)
start = st.sidebar.slider("Trend from year", int(df.month.dt.year.min()), int(latest.year), max(int(df.month.dt.year.min()), 2019))

st.title("NHS Wales Emergency Department Performance")
st.caption(f"Source: StatsWales, Digital Health and Care Wales. Latest month: {latest:%B %Y}. "
           "Targets: 95% within 4 hours, nobody waiting 12 hours or more.")

# ---------- Headline numbers ----------
sel = df[(df.area == area) & (df.unit_type == unit)].sort_values("month")
now = sel[sel.month == latest]
year_ago = sel[sel.month == latest - pd.DateOffset(years=1)]

if now.empty:
    st.warning(f"{area} has no {unit_label[unit].lower()} data for {latest:%B %Y}.")
else:
    n = now.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Attendances", f"{n.total:,.0f}")
    delta = None if year_ago.empty else f"{n.pct_4h - year_ago.iloc[0].pct_4h:+.1f} pts vs last year"
    c2.metric("Within 4 hours", f"{n.pct_4h:.1f}%", delta)
    c3.metric("Gap to 95% target", f"{95 - n.pct_4h:.1f} pts")
    c4.metric("Waited 12 hours or more", f"{n.over_12h:,.0f}", f"{100 - n.pct_12h_or_less:.1f}% of patients",
              delta_color="off")

# ---------- Trend ----------
st.subheader(f"{area}: % within 4 hours")
trend = sel[sel.month.dt.year >= start]
fig = px.line(trend, x="month", y="pct_4h", labels={"month": "", "pct_4h": "% within 4 hours"})
fig.add_hline(y=95, line_dash="dash", annotation_text="95% target")
fig.update_layout(height=350, margin=dict(t=20, b=10))
st.plotly_chart(fig, width="stretch")

# ---------- Board comparison ----------
st.subheader("Health board comparison, last 12 months")
last12 = df[(df.month > latest - pd.DateOffset(months=12)) & (df.unit_type == "All")
            & (df.level == "Health board") & (df.area.isin(current_boards)) & (~df.area.isin(no_major))]
rank = (last12.groupby("area")[["total", "within_4h", "within_12h"]].sum()
              .assign(pct_4h=lambda d: 100 * d.within_4h / d.total,
                      pct_over_12h=lambda d: 100 * (d.total - d.within_12h) / d.total)
              .reset_index())

left, right = st.columns(2)
f1 = px.bar(rank.sort_values("pct_4h"), x="pct_4h", y="area", orientation="h", text_auto=".1f",
            labels={"pct_4h": "% within 4 hours", "area": ""}, title="% within 4 hours (dashed line = 95% target)")
f1.add_vline(x=95, line_dash="dash")
f1.update_layout(height=350, xaxis_range=[0, 100])
left.plotly_chart(f1, width="stretch")
f2 = px.bar(rank.sort_values("pct_over_12h", ascending=False), x="pct_over_12h", y="area", orientation="h",
            text_auto=".1f", labels={"pct_over_12h": "% waiting 12 hours or more", "area": ""},
            title="% waiting 12 hours or more")
f2.update_layout(height=350)
right.plotly_chart(f2, width="stretch")
if no_major:
    st.caption(f"Not ranked: {', '.join(no_major)} (no major emergency department, so not comparable).")

# ---------- Hospitals ----------
hosp = df[(df.level == "Hospital") & (df.unit_type == "Major") & (df.month == latest)]
if area != "Wales":
    board_code = df[df.area == area]["area_code"].iloc[0]
    hosp = hosp[hosp.parent_code == board_code]
if not hosp.empty:
    st.subheader(f"Major emergency departments, {latest:%B %Y}")
    show = hosp[["area", "total", "pct_4h", "over_12h"]].sort_values("pct_4h").rename(columns={
        "area": "Hospital", "total": "Attendances", "pct_4h": "% within 4 hours", "over_12h": "Waited 12h+"})
    st.dataframe(show.style.format({"Attendances": "{:,.0f}", "% within 4 hours": "{:.1f}", "Waited 12h+": "{:,.0f}"}),
                 hide_index=True, width="stretch")

# ---------- Data quality ----------
with st.expander("Data quality log"):
    st.write("Checks run on the raw StatsWales file before analysis. Each finding has the action taken.")
    st.dataframe(dq, hide_index=True, width="stretch")
    st.download_button("Download cleaned data (CSV)", df.to_csv(index=False).encode(), "ed_performance_tidy.csv", "text/csv")
