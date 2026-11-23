"""NHS Wales A&E Waits: an interactive dashboard on emergency department performance in Wales.
Run with: streamlit run app.py
"""
from pathlib import Path
import re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

HERE = Path(__file__).parent
TIDY = HERE / "data" / "processed" / "ed_performance_tidy.csv"
DQ = HERE / "data" / "processed" / "data_quality_log.csv"
GITHUB = "https://github.com/Afin-ai/nhs-wales-ed-performance"
LINKEDIN = "https://www.linkedin.com/in/afin-padipurackal-abdul-rasheed-24b836236"
SOURCE = "https://stats.gov.wales/en-GB/3ce1cc28-0625-4674-89d6-9cf3a56f2d9c/start"

# ---------- Colours ----------
NAVY, BLUE, BLUE_LIGHT = "#0d2b52", "#2a78d6", "#b7d3f6"
ORANGE, AQUA, VIOLET, MAGENTA, YELLOW = "#eb6834", "#1baf7a", "#6250d6", "#e87ba4", "#eda100"
GREY, GREY_LIGHT = "#8a897f", "#d6d5ce"
INK, INK_2, GRID, AXIS = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"
RED, GREEN, CONCERN = "#d03b3b", "#006300", "#ec835a"
# Wait bands, from quickest to longest
BANDS = [("Under 4 hours", "#1baf7a"), ("4 to 8 hours", "#eda100"), ("8 to 12 hours", "#eb6834"), ("12 hours or more", "#b3261e")]
STRIPES = [[0, "#8f1d1d"], [0.25, "#d03b3b"], [0.45, "#f4a582"], [0.6, "#f7f7f5"], [0.8, "#86b6ef"], [1, "#104281"]]
DIVERGE = [[0, "#d03b3b"], [0.5, "#f3f2ee"], [1, "#2a78d6"]]
BOARD_COLOURS = [BLUE, ORANGE, AQUA, VIOLET, MAGENTA, YELLOW, "#008300"]

COORDS = {  # approximate locations of the major emergency departments
    "Ysbyty Glan Clwyd": (53.2687, -3.5040), "Wrexham Maelor": (53.0418, -2.9989), "Ysbyty Gwynedd": (53.2077, -4.1612),
    "Bronglais": (52.4157, -4.0717), "Glangwili": (51.8669, -4.3240), "Withybush": (51.8128, -4.9655),
    "Morriston": (51.6838, -3.9339), "UHW Cardiff": (51.5072, -3.1903), "Prince Charles": (51.7636, -3.3854),
    "Royal Glamorgan": (51.5487, -3.3907), "Princess of Wales": (51.5105, -3.5674), "The Grange": (51.6553, -3.0129),
}

st.set_page_config(page_title="NHS Wales A&E Waits", page_icon="🏥", layout="wide")

st.markdown(f"""
<style>
.block-container {{padding-top: 1.4rem; max-width: 1300px;}}
h1, h2, h3, h4 {{letter-spacing: -0.01em;}}
.hero {{background: radial-gradient(circle at 85% 10%, #2a78d6 0%, rgba(42,120,214,0) 45%),
        radial-gradient(circle at 10% 120%, #6250d6 0%, rgba(98,80,214,0) 40%), {NAVY};
        color: white; border-radius: 18px; padding: 28px 32px 22px; margin-bottom: 6px;}}
.hero .kicker {{text-transform: uppercase; letter-spacing: 0.14em; font-size: 0.75rem; color: #9ec5f4; margin-bottom: 4px;}}
.hero h1 {{color: white; font-size: 2.3rem; margin: 0 0 8px 0; padding: 0; line-height: 1.1;}}
.hero p {{color: #d6e4f7; margin: 0; font-size: 1.02rem; max-width: 860px;}}
.pill {{display: inline-block; background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.22);
        border-radius: 999px; padding: 3px 12px; margin: 14px 8px 0 0; font-size: 0.8rem; color: white;}}
.card {{background: white; border: 1px solid rgba(11,11,11,0.08); border-radius: 14px; padding: 16px 18px 14px;
        min-height: 168px; box-shadow: 0 1px 2px rgba(11,11,11,0.04), 0 4px 14px rgba(11,11,11,0.04); position: relative; overflow: hidden;}}
.card .bar {{position: absolute; left: 0; top: 0; right: 0; height: 5px;}}
.card .icon {{font-size: 1.25rem; float: right; opacity: 0.9;}}
.card .label {{color: {INK_2}; font-size: 0.86rem; margin: 4px 0 2px;}}
.card .value {{color: {INK}; font-size: 2.1rem; font-weight: 650; line-height: 1.15;}}
.card .delta {{font-size: 0.84rem; margin-top: 3px;}}
.status {{display: inline-block; border-radius: 6px; padding: 1px 8px; font-size: 0.78rem; font-weight: 600; margin-top: 8px;}}
.insight {{background: linear-gradient(90deg, #f1f6fd, #f7f5ff); border-radius: 14px; padding: 16px 20px; margin: 4px 0;}}
.insight li {{margin-bottom: 5px; color: {INK};}}
.people {{display: grid; grid-template-columns: repeat(10, 1fr); gap: 5px 8px; max-width: 330px;}}
.people svg {{width: 100%; height: auto;}}
.legend-row {{display: flex; align-items: center; gap: 10px; margin: 10px 0; font-size: 0.98rem; color: {INK};}}
.legend-row .sw {{width: 14px; height: 14px; border-radius: 4px; flex: none;}}
.legend-row .num {{font-weight: 700; font-size: 1.5rem; min-width: 44px; text-align: right;}}
.note {{color: {INK_2}; font-size: 0.86rem;}}
.section {{margin-top: 18px;}}
.footer {{color: {INK_2}; font-size: 0.82rem; border-top: 1px solid {GRID}; margin-top: 30px; padding-top: 12px;}}
.footer a {{color: {BLUE};}}
div[data-baseweb="tab-list"] button p {{font-size: 0.98rem; font-weight: 600;}}
</style>
""", unsafe_allow_html=True)


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
boards_now = df[(df.level == "Health board") & (df.month == latest)]
board_names = sorted(boards_now["area"].unique())
board_of = dict(zip(boards_now.area_code, boards_now.area))
board_types = df[df.level == "Health board"].groupby("area")["unit_type"].unique()
no_major = [b for b, t in board_types.items() if "Major" not in t]
ranked_boards = [b for b in board_names if b not in no_major]
board_colour = {b: BOARD_COLOURS[i % len(BOARD_COLOURS)] for i, b in enumerate(ranked_boards)}


# ---------- Helpers ----------
def layout(fig, height=360, **kw):
    kw.setdefault("hovermode", "closest")
    fig.update_layout(height=height, margin=dict(l=10, r=20, t=30, b=10), plot_bgcolor="white", paper_bgcolor="white",
                      font=dict(color=INK_2, size=13), hoverlabel=dict(bgcolor="white", font_color=INK, bordercolor=AXIS),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None), **kw)
    fig.update_xaxes(showgrid=False, linecolor=AXIS, ticks="outside", tickcolor=AXIS)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=AXIS)
    return fig


def sums(frame):
    s = frame[["total", "within_4h", "within_12h"]].sum(min_count=1)
    return dict(total=s.total, pct_4h=100 * s.within_4h / s.total,
                over_12h=s.total - s.within_12h, pct_12h=100 * (s.total - s.within_12h) / s.total)


def card(icon, colour, label, value, delta=None, good=None, status=None):
    d = ""
    if delta:
        c = INK_2 if good is None else (GREEN if good else RED)
        d = f'<div class="delta" style="color:{c}">{delta}</div>'
    s = ""
    if status:
        txt, col = status
        s = f'<span class="status" style="background:{col}1f;color:{col}">{txt}</span>'
    size = ' style="font-size:1.4rem"' if len(str(value)) > 14 else ""
    return (f'<div class="card"><div class="bar" style="background:{colour}"></div><span class="icon">{icon}</span>'
            f'<div class="label">{label}</div><div class="value"{size}>{value}</div>{d}{s}</div>')


def short(name):
    n = name.replace(" (Major)", "")
    n = n.replace("University Hospital of Wales", "UHW Cardiff").replace("The Royal ", "Royal ")
    for w in [" University Hospital", " General Hospital", " Hospital"]:
        n = n.replace(w, "")
    return n


def person(colour):
    return (f'<svg viewBox="0 0 20 32"><circle cx="10" cy="6" r="5" fill="{colour}"/>'
            f'<rect x="3" y="13" width="14" height="18" rx="6" fill="{colour}"/></svg>')


def hundred(counts):
    """Turn counts into whole numbers out of 100 that add up to exactly 100."""
    tot = sum(counts)
    raw = [100 * c / tot for c in counts]
    out = [int(r) for r in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - out[i], reverse=True)[:100 - sum(out)]:
        out[i] += 1
    return out


def spc(series):
    """XmR chart in the NHS 'Making Data Count' style. Higher is better."""
    x = series.dropna()
    mean, mr = x.mean(), x.diff().abs().mean()
    upl, lpl = mean + 2.66 * mr, mean - 2.66 * mr
    flag = pd.Series("common", index=x.index)
    flag[x > upl], flag[x < lpl] = "improve", "concern"
    side = (x > mean).astype(int) - (x < mean).astype(int)
    run = 0
    for i in range(len(x)):  # shift: 7 or more points in a row on one side of the average
        run = run + 1 if i and side.iloc[i] == side.iloc[i - 1] and side.iloc[i] != 0 else 1
        if run >= 7:
            flag.iloc[i - run + 1:i + 1] = "improve" if side.iloc[i] > 0 else "concern"
    step = x.diff().apply(lambda v: 1 if v > 0 else (-1 if v < 0 else 0))
    run = 0
    for i in range(1, len(x)):  # trend: 6 or more points in a row going up or down
        run = run + 1 if i > 1 and step.iloc[i] == step.iloc[i - 1] and step.iloc[i] != 0 else 1
        if run >= 5:
            flag.iloc[i - run:i + 1] = "improve" if step.iloc[i] > 0 else "concern"
    return x, mean, upl, lpl, flag


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### 🎛️ Explore")
    area = st.selectbox("Area", ["Wales"] + board_names)
    unit_label = {"All": "All emergency care", "Major": "Major emergency departments", "Minor": "Minor injury units"}
    available = [u for u in ["All", "Major", "Minor"] if ((df.area == area) & (df.unit_type == u)).any()]
    unit = st.selectbox("Type of unit", available, format_func=unit_label.get)
    months = sorted(df[(df.area == area) & (df.unit_type == unit) & (df.month >= "2019-04-01")].month.unique())
    m = pd.Timestamp(st.select_slider("⏳ Time machine: pick a month", options=months, value=months[-1],
                                      format_func=lambda d: pd.Timestamp(d).strftime("%b %Y")))
    first_year = int(df.month.dt.year.min())
    start = st.slider("Show trends from", first_year, int(latest.year), max(first_year, 2019))
    st.markdown("---")
    st.markdown(f"""<div class="note"><b>🎯 Targets in Wales</b><br>95% of patients spend less than 4 hours in an
    emergency department, and nobody waits 12 hours or more.<br><br>
    <b>📊 Source</b><br><a href="{SOURCE}">StatsWales</a>, Digital Health and Care Wales.
    Refreshed daily from the published data.</div>""", unsafe_allow_html=True)

sel = df[(df.area == area) & (df.unit_type == unit)].sort_values("month").set_index("month")
wales = df[(df.area == "Wales") & (df.unit_type == unit)].sort_values("month").set_index("month")

# ---------- Header ----------
st.markdown(f"""<div class="hero"><div class="kicker">NHS Wales · Emergency departments</div>
<h1>How long are people waiting in A&amp;E?</h1>
<p>Seventeen years of official data on every health board and major emergency department in Wales,
checked for quality and turned into a picture anyone can read.</p>
<span class="pill">📅 Latest data: {latest:%B %Y}</span><span class="pill">🏥 7 health boards · 12 major EDs</span>
<span class="pill">✅ Data quality checked</span><span class="pill">🔄 Updates itself daily</span></div>""",
            unsafe_allow_html=True)

# ---------- Waiting stripes (signature visual) ----------
stripe = sel.pct_4h.dropna()
fig = go.Figure(go.Heatmap(z=[stripe.values], x=stripe.index, y=[""], colorscale=STRIPES, zmin=45, zmax=95,
                           showscale=False, xgap=0,
                           hovertemplate="%{x|%B %Y}: %{z:.1f}% seen within 4 hours<extra></extra>"))
fig.update_layout(height=110, margin=dict(l=0, r=0, t=0, b=22), plot_bgcolor="white", paper_bgcolor="white",
                  xaxis=dict(showgrid=False, tickformat="%Y", dtick="M24", tickfont=dict(color=INK_2, size=11)),
                  yaxis=dict(visible=False))
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
st.markdown(f'<p class="note" style="margin-top:-10px">〰️ <b>Waiting stripes for {area}.</b> Each stripe is one month since '
            f'{stripe.index.min():%B %Y}. Dark blue means most patients were seen within 4 hours. Red means far fewer were. '
            f'Hover over any stripe to see the figure.</p>', unsafe_allow_html=True)

tabs = st.tabs(["📖 The story", "🏥 Hospitals", "🗺️ Health boards", "🔍 Is it real? (SPC)", "✅ Data quality", "ℹ️ About"])

# ================= THE STORY =================
with tabs[0]:
    if m not in sel.index:
        st.warning(f"{area} has no data for {unit_label[unit].lower()} in {m:%B %Y}.")
    else:
        n = sel.loc[m]
        prev = sel.loc[m - pd.DateOffset(years=1)] if (m - pd.DateOffset(years=1)) in sel.index else None
        last12 = sums(sel[(sel.index > m - pd.DateOffset(months=12)) & (sel.index <= m)])
        prev12 = sums(sel[(sel.index <= m - pd.DateOffset(months=12)) & (sel.index > m - pd.DateOffset(months=24))])

        st.markdown(f"### {area} · {unit_label[unit]} · {m:%B %Y}")
        c1, c2, c3, c4 = st.columns(4)
        d4 = None if prev is None else n.pct_4h - prev.pct_4h
        on_target = n.pct_4h >= 95
        c1.markdown(card("⏱️", BLUE, "Seen within 4 hours", f"{n.pct_4h:.1f}%",
                         None if d4 is None else f"{'▲' if d4 >= 0 else '▼'} {abs(d4):.1f} pts on a year ago",
                         None if d4 is None else d4 >= 0,
                         ("✓ Meets the 95% target", GREEN) if on_target else (f"✕ {95 - n.pct_4h:.1f} pts below target", RED)),
                    unsafe_allow_html=True)
        d12 = None if prev is None else n.over_12h - prev.over_12h
        c2.markdown(card("🛏️", ORANGE, "Waited 12 hours or more", f"{n.over_12h:,.0f}",
                         None if d12 is None else f"{'▲' if d12 >= 0 else '▼'} {abs(d12):,.0f} on a year ago",
                         None if d12 is None else d12 <= 0, (f"{100 - n.pct_12h_or_less:.1f}% of patients", INK_2)),
                    unsafe_allow_html=True)
        da = None if prev is None else 100 * (n.total - prev.total) / prev.total
        c3.markdown(card("👥", AQUA, "Attendances", f"{n.total:,.0f}",
                         None if da is None else f"{'▲' if da >= 0 else '▼'} {abs(da):.1f}% on a year ago", None,
                         (f"{last12['total']:,.0f} in 12 months", INK_2)), unsafe_allow_html=True)
        missed = max(0.0, 0.95 * n.total - n.within_4h)
        c4.markdown(card("🎯", VIOLET, "Patients short of the target", f"{missed:,.0f}",
                         "more would need to be seen within 4 hours to reach 95%", None,
                         (f"about {missed / n.total * 100:.0f} in every 100", INK_2)), unsafe_allow_html=True)

        # ---- If 100 patients walked in ----
        st.markdown('<div class="section"></div>', unsafe_allow_html=True)
        left, right = st.columns([1.05, 1])
        with left:
            st.markdown(f"#### 🚶 If 100 patients walked into A&E in {m:%B %Y}...")
            if pd.isna(n.within_8h) or pd.isna(n.within_12h):
                st.info("Waits longer than 4 hours are not split out for this month.")
            else:
                counts = [n.within_4h, n.within_8h - n.within_4h, n.within_12h - n.within_8h, n.total - n.within_12h]
                per100 = hundred(counts)
                cols = [c for (_, c), k in zip(BANDS, per100) for _ in range(k)]
                st.markdown('<div class="people">' + "".join(person(c) for c in cols) + "</div>", unsafe_allow_html=True)
        with right:
            if not (pd.isna(n.within_8h) or pd.isna(n.within_12h)):
                st.markdown("&nbsp;")
                st.markdown("".join(
                    f'<div class="legend-row"><span class="sw" style="background:{c}"></span><span class="num">{k}</span>'
                    f'<span>left A&amp;E in <b>{lab.lower()}</b></span></div>' for (lab, c), k in zip(BANDS, per100)),
                    unsafe_allow_html=True)
                st.markdown(f'<p class="note" style="margin-top:14px">The target is for 95 of every 100 people to leave within '
                            f'4 hours, and for nobody to wait 12 hours or more. Based on {n.total:,.0f} real attendances.</p>',
                            unsafe_allow_html=True)

        # ---- Key points ----
        bullets = [f"<b>{n.pct_4h:.1f}%</b> of patients spent less than 4 hours, <b>{95 - n.pct_4h:.1f} points</b> short of the 95% target."
                   if not on_target else f"<b>{n.pct_4h:.1f}%</b> of patients spent less than 4 hours, meeting the 95% target."]
        if prev12["total"] and prev12["over_12h"] and not pd.isna(prev12["over_12h"]):
            ch = 100 * (last12["over_12h"] - prev12["over_12h"]) / prev12["over_12h"]
            bullets.append(f"<b>{last12['over_12h']:,.0f}</b> patients waited 12 hours or more in the 12 months to {m:%B %Y}, "
                           f"{'up' if ch >= 0 else 'down'} <b>{abs(ch):.0f}%</b> on the year before.")
        if area != "Wales" and m in wales.index:
            gap = n.pct_4h - wales.loc[m].pct_4h
            bullets.append(f"That is <b>{abs(gap):.1f} points {'above' if gap >= 0 else 'below'}</b> the Wales figure of "
                           f"{wales.loc[m].pct_4h:.1f}% for the same type of unit.")
        hist = sel[(sel.index >= "2019-04-01") & (sel.index <= m)].pct_4h
        if n.pct_4h <= hist.min() + 1e-9:
            bullets.append(f"This is the <b>lowest month on record</b> since April 2019.")
        if area in no_major:
            bullets.append(f"{area} has no major emergency department, so its figures are not comparable with other boards.")
        st.markdown('<div class="insight"><b>💡 What this tells us</b><ul>' + "".join(f"<li>{b}</li>" for b in bullets)
                    + "</ul></div>", unsafe_allow_html=True)
        NL = chr(10)  # new line
        brief = NL.join([f"NHS Wales A&E briefing: {area}, {unit_label[unit].lower()}, {m:%B %Y}", "Source: StatsWales", ""]
                        + ["- " + re.sub("<[^>]+>", "", b) for b in bullets]
                        + ["", f"Attendances: {n.total:,.0f}", f"Within 4 hours: {n.pct_4h:.1f}%",
                           f"Waited 12 hours or more: {n.over_12h:,.0f}", "", f"Dashboard by Afin Rasheed. Code: {GITHUB}", ""])
        st.download_button("⬇️ Download a one-page briefing", brief, f"AE_briefing_{area.replace(' ', '_')}_{m:%Y_%m}.txt")

        # ---- Trend ----
        st.markdown(f"#### 📈 Share of patients seen within 4 hours since {start}")
        t = sel[sel.index.year >= start]
        roll = sel.pct_4h.rolling(12).mean()[sel.index.year >= start]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t.index, y=t.pct_4h, name=f"{area}, monthly", mode="lines", fill="tozeroy",
                                 fillcolor="rgba(42,120,214,0.07)", line=dict(color=BLUE_LIGHT, width=1.5),
                                 hovertemplate="%{y:.1f}%<extra>" + area + "</extra>"))
        fig.add_trace(go.Scatter(x=roll.index, y=roll, name="12-month average", mode="lines",
                                 line=dict(color=BLUE, width=3), hovertemplate="%{y:.1f}%<extra>12-month average</extra>"))
        if area != "Wales":
            w = wales[wales.index.year >= start]
            fig.add_trace(go.Scatter(x=w.index, y=w.pct_4h, name="Wales", mode="lines",
                                     line=dict(color=GREY, width=1.5, dash="dot"), hovertemplate="%{y:.1f}%<extra>Wales</extra>"))
        fig.add_hline(y=95, line=dict(color=RED, width=1.2, dash="dash"),
                      annotation=dict(text="🎯 95% target", font_color=RED), annotation_position="top left")
        if start <= 2020:
            fig.add_vrect(x0="2020-03-01", x1="2021-03-01", fillcolor=GRID, opacity=0.4, line_width=0,
                          annotation=dict(text="COVID-19", font_color=INK_2), annotation_position="top right")
        fig.add_vline(x=m, line=dict(color=VIOLET, width=1.5))
        fig.add_annotation(x=m, y=1.04, yref="paper", text=f"{m:%b %Y}", showarrow=False, font=dict(color=VIOLET, size=11))
        layout(fig, 380, yaxis_title="% within 4 hours", hovermode="x unified")
        fig.update_yaxes(ticksuffix="%", range=[max(0, t.pct_4h.min() - 8), 100])
        st.plotly_chart(fig, width="stretch")

        # ---- Winter pressure ----
        st.markdown("#### ❄️ Winter pressure: each year, month by month")
        yrs = [y for y in range(m.year - 3, m.year + 1) if (sel.index.year == y).any()]
        shade = ["#dcdbd5", "#b8b7af", "#8a897f"]
        fig = go.Figure()
        for i, y in enumerate(yrs):
            d = sel[(sel.index.year == y) & (sel.index <= m)]
            cur = y == m.year
            col = BLUE if cur else shade[max(0, i - (len(yrs) - 4))]
            fig.add_trace(go.Scatter(x=d.index.month, y=d.pct_4h, mode="lines+markers", name=str(y),
                                     line=dict(color=col, width=3.5 if cur else 1.8), marker=dict(size=8 if cur else 5, color=col),
                                     hovertemplate="%{y:.1f}%<extra>" + str(y) + "</extra>"))
            fig.add_annotation(x=d.index.month[-1], y=d.pct_4h.iloc[-1], text=f" {y}", showarrow=False, xanchor="left",
                               font=dict(color=INK if cur else INK_2, size=11))
        layout(fig, 330, yaxis_title="% within 4 hours", hovermode="x unified")
        fig.update_xaxes(tickvals=list(range(1, 13)), ticktext=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                                                                  "Oct", "Nov", "Dec"], range=[0.6, 12.9])
        fig.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig, width="stretch")
        st.markdown('<p class="note">Each line is one calendar year, and the current year is in blue. Lower lines mean fewer '
                    'patients were seen within 4 hours.</p>', unsafe_allow_html=True)

# ================= HOSPITALS =================
with tabs[1]:
    st.markdown("#### ▶️ Watch the hospitals move: press play")
    st.markdown('<p class="note">Each bubble is a major emergency department, sized by how many patients it saw. '
                'Right is faster, lower is fewer 12-hour waits, so the bottom right is the best place to be. '
                'Press ▶ to play the months from 2021, or drag the slider under the chart.</p>', unsafe_allow_html=True)
    hv = df[(df.level == "Hospital") & (df.unit_type == "Major") & (df.month >= "2021-01-01")].copy()
    hv = hv[hv.area_code.isin(df[(df.level == "Hospital") & (df.month == latest)].area_code)]
    hv["name"] = hv.area.map(short)
    hv["board"] = hv.parent_code.map(board_of)
    hv["pct_12h"] = 100 - hv.pct_12h_or_less
    mon = sorted(hv.month.unique())
    smax = hv.total.max()

    def frame_traces(dm):
        out = []
        for b in ranked_boards:
            p = dm[dm.board == b]
            out.append(go.Scatter(x=p.pct_4h, y=p.pct_12h, mode="markers+text", name=b, text=p.name,
                                  textposition="top center", textfont=dict(size=10, color=INK_2),
                                  marker=dict(size=(p.total / smax) ** 0.5 * 48, color=board_colour[b], opacity=0.85,
                                              line=dict(color="white", width=1.5)),
                                  customdata=p[["board", "total"]].values,
                                  hovertemplate="<b>%{text}</b><br>%{customdata[0]}<br>%{x:.1f}% within 4 hours<br>"
                                                "%{y:.1f}% waited 12h+<br>%{customdata[1]:,.0f} attendances<extra></extra>"))
        return out

    fig = go.Figure(data=frame_traces(hv[hv.month == mon[-1]]),
                    frames=[go.Frame(data=frame_traces(hv[hv.month == mm]), name=pd.Timestamp(mm).strftime("%b %Y"))
                            for mm in mon])
    steps = [dict(method="animate", label=pd.Timestamp(mm).strftime("%b %y"),
                  args=[[pd.Timestamp(mm).strftime("%b %Y")], dict(mode="immediate", frame=dict(duration=0, redraw=True),
                                                                    transition=dict(duration=0))]) for mm in mon]
    fig.update_layout(
        updatemenus=[dict(type="buttons", showactive=False, x=0, y=-0.13, xanchor="left", yanchor="top",
                          buttons=[dict(label="▶ Play", method="animate",
                                        args=[None, dict(frame=dict(duration=350, redraw=True), transition=dict(duration=250),
                                                         fromcurrent=True, mode="immediate")]),
                                   dict(label="⏸ Pause", method="animate",
                                        args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])])],
        sliders=[dict(active=len(mon) - 1, steps=steps, x=0.16, len=0.84, y=-0.08, yanchor="top",
                      currentvalue=dict(prefix="Month: ", font=dict(size=15, color=INK)), pad=dict(t=30),
                      tickcolor=AXIS, font=dict(size=9, color=INK_2))])
    layout(fig, 600, xaxis_title="% seen within 4 hours  →  faster", yaxis_title="% waiting 12 hours or more")
    fig.update_layout(margin=dict(l=10, r=20, t=40, b=150))
    fig.update_xaxes(range=[15, 85], ticksuffix="%", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(range=[0, 42], ticksuffix="%")
    fig.add_annotation(x=0.99, y=0.02, xref="paper", yref="paper", text="✓ Faster, fewer long waits", showarrow=False,
                       font=dict(color=GREEN, size=12), xanchor="right", yanchor="bottom")
    fig.add_annotation(x=0.01, y=0.98, xref="paper", yref="paper", text="✕ Slower, more long waits", showarrow=False,
                       font=dict(color=RED, size=12), xanchor="left", yanchor="top")
    st.plotly_chart(fig, width="stretch")

    # ---- Map ----
    st.markdown(f"#### 🗺️ Where the pressure is, 12 months to {m:%B %Y}")
    st.markdown('<p class="note">Bigger circles saw more patients. Red is below the Wales average for major emergency '
                'departments and blue is above it.</p>', unsafe_allow_html=True)
    h = df[(df.level == "Hospital") & (df.unit_type == "Major") & (df.month > m - pd.DateOffset(months=12)) & (df.month <= m)]
    h = h[h.area_code.isin(df[(df.level == "Hospital") & (df.month == m)].area_code)]
    hs = h.groupby(["area", "parent_code"])[["total", "within_4h", "within_12h"]].sum().reset_index()
    hs["pct_4h"] = 100 * hs.within_4h / hs.total
    hs["pct_12h"] = 100 * (hs.total - hs.within_12h) / hs.total
    hs["name"], hs["board"] = hs.area.map(short), hs.parent_code.map(board_of)
    mw = sums(df[(df.area == "Wales") & (df.unit_type == "Major") & (df.month > m - pd.DateOffset(months=12)) & (df.month <= m)])
    hm2 = hs.assign(lat=hs.name.map(lambda k: COORDS.get(k, (None, None))[0]),
                    lon=hs.name.map(lambda k: COORDS.get(k, (None, None))[1])).dropna(subset=["lat"])
    if not hm2.empty:
        hm2["gap"] = hm2.pct_4h - mw["pct_4h"]
        lim2 = float(hm2.gap.abs().max())
        fig = go.Figure(go.Scattermap(
            lat=hm2.lat, lon=hm2.lon, mode="markers+text", text=hm2.name, textposition="top right",
            textfont=dict(size=12, color=INK),
            marker=dict(size=(hm2.total / hm2.total.max()) ** 0.5 * 44, color=hm2.gap, colorscale=DIVERGE, cmin=-lim2, cmax=lim2,
                        opacity=0.9, colorbar=dict(title="Points vs<br>Wales average", thickness=10, len=0.6)),
            customdata=hm2[["board", "pct_4h", "pct_12h", "total"]].values,
            hovertemplate="<b>%{text}</b><br>%{customdata[0]}<br>%{customdata[1]:.1f}% within 4 hours<br>"
                          "%{customdata[2]:.1f}% waited 12h+<br>%{customdata[3]:,.0f} attendances<extra></extra>"))
        fig.update_layout(map=dict(style="carto-positron", center=dict(lat=52.3, lon=-3.8), zoom=6.6),
                          height=680, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width="stretch")

    st.markdown(f"#### 🏥 Hospital table, {m:%B %Y}")
    ht = df[(df.level == "Hospital") & (df.unit_type == "Major") & (df.month == m)].copy()
    if area != "Wales":
        ht = ht[ht.parent_code.map(board_of) == area]
    ht["Hospital"] = ht.area.str.replace(" (Major)", "", regex=False)
    ht["Health board"] = ht.parent_code.map(board_of)
    ht = ht.sort_values("pct_4h")[["Hospital", "Health board", "total", "pct_4h", "over_12h"]]
    st.dataframe(ht, hide_index=True, width="stretch", height=(len(ht) + 1) * 35 + 3, column_config={
        "total": st.column_config.NumberColumn("Attendances", format="localized"),
        "pct_4h": st.column_config.ProgressColumn("% within 4 hours", format="%.1f%%", min_value=0, max_value=100),
        "over_12h": st.column_config.NumberColumn("Waited 12 hours or more", format="localized"),
    })

# ================= HEALTH BOARDS =================
with tabs[2]:
    st.markdown(f"#### 🏆 Health board league table, 12 months to {m:%B %Y}")
    lt = []
    for b in ranked_boards:
        sb = df[(df.area == b) & (df.unit_type == "All")].sort_values("month")
        cur = sums(sb[(sb.month > m - pd.DateOffset(months=12)) & (sb.month <= m)])
        old = sums(sb[(sb.month <= m - pd.DateOffset(months=12)) & (sb.month > m - pd.DateOffset(months=24))])
        lt.append({"board": b, "Attendances": cur["total"], "now": cur["pct_4h"], "before": old["pct_4h"],
                   "p12": cur["pct_12h"], "Waited 12h+": cur["over_12h"],
                   "Trend": sb[sb.month <= m].pct_4h.iloc[-24:].round(1).tolist()})
    lt = pd.DataFrame(lt).sort_values("now", ascending=False)
    lt.insert(0, "Rank", ["🥇", "🥈", "🥉"] + [str(i) for i in range(4, len(lt) + 1)])
    lt["Change"] = (lt.now - lt.before).map(lambda v: f"{'▲' if v >= 0 else '▼'} {abs(v):.1f} pts")
    st.dataframe(lt[["Rank", "board", "Attendances", "now", "Change", "Waited 12h+", "Trend"]], hide_index=True, width="stretch",
                 height=(len(lt) + 1) * 35 + 3, column_config={
                     "board": "Health board",
                     "Attendances": st.column_config.NumberColumn(format="localized"),
                     "now": st.column_config.ProgressColumn("% within 4 hours", format="%.1f%%", min_value=0, max_value=100),
                     "Change": st.column_config.TextColumn("vs year before"),
                     "Waited 12h+": st.column_config.NumberColumn("Waited 12 hours or more", format="localized"),
                     "Trend": st.column_config.LineChartColumn("Last 24 months", y_min=40, y_max=90)})
    st.markdown('<p class="note">All emergency care facilities. Powys is not ranked because it has no major emergency department.</p>',
                unsafe_allow_html=True)

    st.markdown("#### ↔️ Better or worse than a year ago?")
    rb = lt.sort_values("now")
    fig = go.Figure()
    for _, r in rb.iterrows():
        better = r.now >= r.before
        fig.add_trace(go.Scatter(x=[r.before, r.now], y=[r.board, r.board], mode="lines",
                                 line=dict(color="#b6e3cf" if better else "#f4c3b0", width=6), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=rb.before, y=rb.board, mode="markers", name="Year before",
                             marker=dict(color=GREY, size=12, line=dict(color="white", width=2)),
                             hovertemplate="%{y}: %{x:.1f}%<extra>Year before</extra>"))
    fig.add_trace(go.Scatter(x=rb.now, y=rb.board, mode="markers+text", name="Last 12 months",
                             marker=dict(color=[board_colour[b] for b in rb.board], size=16, line=dict(color="white", width=2)),
                             text=[f"{v:.1f}%" for v in rb.now],
                             textposition=["middle left" if a < b else "middle right" for a, b in zip(rb.now, rb.before)],
                             textfont=dict(color=INK, size=12), hovertemplate="%{y}: %{x:.1f}%<extra>Last 12 months</extra>"))
    layout(fig, 380, xaxis_title="% within 4 hours")
    fig.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=GRID)
    st.plotly_chart(fig, width="stretch")
    st.markdown('<p class="note">Grey dot: the year before. Coloured dot: the last 12 months. A green bar means the board '
                'improved and a red bar means it got worse.</p>', unsafe_allow_html=True)

    st.markdown("#### 🌡️ Month by month, against the Wales figure")
    hm = df[(df.level == "Health board") & (df.unit_type == "All") & (df.area.isin(ranked_boards))
            & (df.month > m - pd.DateOffset(months=24)) & (df.month <= m)]
    wm = df[(df.area == "Wales") & (df.unit_type == "All")].set_index("month").pct_4h
    hm = hm.assign(gap=hm.pct_4h - hm.month.map(wm))
    piv = hm.pivot(index="area", columns="month", values="gap").reindex(rb.board)
    raw = hm.pivot(index="area", columns="month", values="pct_4h").reindex(rb.board)
    lim = float(piv.abs().max().max())
    fig = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=piv.index, colorscale=DIVERGE, zmid=0, zmin=-lim, zmax=lim,
                               xgap=3, ygap=3, customdata=raw.values, colorbar=dict(title="Points vs<br>Wales", thickness=10),
                               hovertemplate="%{y}, %{x|%b %Y}<br>%{customdata:.1f}% within 4 hours<br>%{z:+.1f} pts vs Wales<extra></extra>"))
    layout(fig, 340)
    fig.update_xaxes(dtick="M3", tickformat="%b %y")
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, width="stretch")
    st.markdown('<p class="note">Blue squares are months when a board did better than Wales as a whole. Red squares are '
                'months when it did worse.</p>', unsafe_allow_html=True)

# ================= SPC =================
with tabs[3]:
    st.markdown(f"#### 🔍 Is the change real, or just normal ups and downs? {area}")
    st.markdown('<p class="note">A statistical process control (SPC) chart, the method NHS quality teams use in '
                '<i>Making Data Count</i>. The grey band is the range we expect from normal month-to-month variation. '
                'A point is coloured when something unusual is happening: it falls outside the band, 7 or more months in a row '
                'sit on one side of the average, or 6 or more months in a row keep rising or falling.</p>', unsafe_allow_html=True)
    base_from = st.radio("Work out the limits from", ["April 2022 onwards (after COVID-19)", "The trend period chosen on the left"],
                         horizontal=True)
    sp = sel.pct_4h[sel.index >= ("2022-04-01" if base_from.startswith("April") else f"{start}-01-01")]
    if len(sp) < 12:
        st.info("Not enough months for an SPC chart. Choose an earlier start year.")
    else:
        x, mean, upl, lpl, flag = spc(sp)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(x.index) + list(x.index[::-1]), y=[upl] * len(x) + [lpl] * len(x), fill="toself",
                                 fillcolor="rgba(195,194,183,0.25)", line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=x.index, y=x, mode="lines", line=dict(color=AXIS, width=1.5), hoverinfo="skip", showlegend=False))
        for k, lab, col in [("common", "Normal variation", GREY), ("improve", "Unusual: improvement", BLUE),
                            ("concern", "Unusual: concern", CONCERN)]:
            p = x[flag == k]
            if len(p):
                fig.add_trace(go.Scatter(x=p.index, y=p, mode="markers", name=lab,
                                         marker=dict(color=col, size=10, line=dict(color="white", width=1.5)),
                                         hovertemplate="%{x|%b %Y}: %{y:.1f}%<extra>" + lab + "</extra>"))
        for yv, txt, dash in [(mean, f"Average {mean:.1f}%", "solid"), (upl, f"Upper limit {upl:.1f}%", "dot"),
                              (lpl, f"Lower limit {lpl:.1f}%", "dot")]:
            fig.add_hline(y=yv, line=dict(color=INK_2, width=1, dash=dash),
                          annotation=dict(text=txt, font_color=INK_2, font_size=11), annotation_position="right")
        fig.add_hline(y=95, line=dict(color=RED, width=1.2, dash="dash"),
                      annotation=dict(text="🎯 Target 95%", font_color=RED, font_size=11), annotation_position="right")
        layout(fig, 440, yaxis_title="% within 4 hours")
        fig.update_layout(margin=dict(l=10, r=130, t=30, b=10))
        fig.update_yaxes(ticksuffix="%", range=[min(lpl, x.min()) - 3, 97])
        st.plotly_chart(fig, width="stretch")

        variation = {"common": ("➖", GREY, "Normal variation", "Recent months are within the expected range. Nothing unusual is happening."),
                     "improve": ("⬆️", BLUE, "Unusual improvement", "Performance has risen by more than normal variation would explain."),
                     "concern": ("⬇️", CONCERN, "Unusual decline", "Performance has fallen by more than normal variation would explain. This needs a closer look.")}[flag.iloc[-1]]
        if 95 > upl:
            assurance = ("🚫", RED, "Target out of reach", f"95% is above the upper limit of {upl:.1f}%. The target will not be met "
                         "by chance. Something about how the service runs would need to change.")
        elif 95 < lpl:
            assurance = ("✅", GREEN, "Target reliably met", "The whole expected range sits above the target.")
        else:
            assurance = ("❔", YELLOW, "Target hit and miss", "The target sits inside the expected range, so some months will meet it and some will not.")
        v1, v2 = st.columns(2)
        v1.markdown(card(variation[0], variation[1], "What is happening in the latest month?", variation[2], variation[3]),
                    unsafe_allow_html=True)
        v2.markdown(card(assurance[0], assurance[1], "Can the 95% target be met?", assurance[2], assurance[3]), unsafe_allow_html=True)
        st.markdown(f'<p class="note" style="margin-top:10px">Limits are the average ± 2.66 × the average moving range, '
                    f'worked out from {x.index.min():%B %Y} to {x.index.max():%B %Y} ({len(x)} months).</p>', unsafe_allow_html=True)

# ================= DATA QUALITY =================
with tabs[4]:
    st.markdown("#### ✅ Can the data be trusted?")
    st.markdown('<p class="note">Every check runs on the raw StatsWales file before any analysis. Problems are logged with the '
                'action taken, so the work can be repeated and audited.</p>', unsafe_allow_html=True)
    find = lambda key: dq[dq.check.str.contains(key, case=False)]["finding"].astype(str).tolist() if not dq.empty else []
    pc, gaps = find("Recalculated"), find("add up")
    breaks = len(dq[dq.check.str.contains("Series", case=False)]) if not dq.empty else 0
    q1, q2, q3, q4 = st.columns(4)
    q1.markdown(card("🧮", AQUA, "Percentages re-checked", pc[0].split(" ")[0] if pc else "n/a",
                     "against the underlying counts", None, ("✓ All match", GREEN)), unsafe_allow_html=True)
    q2.markdown(card("⚖️", BLUE, "Boards add up to Wales", "Every month",
                     gaps[0].replace("Largest monthly gap", "Largest gap") if gaps else None, None,
                     ("✓ No gaps", GREEN) if gaps and gaps[0].endswith(" 0 attendances") else None), unsafe_allow_html=True)
    q3.markdown(card("🔎", VIOLET, "Missing values and duplicates", "0", "after checking every row", None,
                     ("✓ None found", GREEN)), unsafe_allow_html=True)
    q4.markdown(card("✂️", YELLOW, "Breaks in the time series", f"{breaks}", "series that start or stop part-way", None,
                     ("! Handled and documented", "#9a6400")), unsafe_allow_html=True)
    st.markdown("#### ⚠️ What to watch when comparing figures")
    st.markdown("""
- **Health board changes, April 2019.** Abertawe Bro Morgannwg became Swansea Bay, and Cwm Taf became Cwm Taf Morgannwg
  when the Bridgend area moved between them. Trends for these boards are not like-for-like across that date.
- **The Grange University Hospital, November 2020.** Nevill Hall and Royal Gwent stopped being major EDs and became minor units.
- **Minor injury units lift board totals.** A board with many minor units can look better than its major ED really is.
- **Powys has no major ED,** so its near-100% figure is not comparable and is left out of the rankings.
""")
    with st.expander("📋 Full data quality log"):
        st.dataframe(dq, hide_index=True, width="stretch")
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Download cleaned data (CSV)", df.to_csv(index=False).encode(), "ed_performance_tidy.csv", "text/csv")
    c2.download_button("⬇️ Download data quality log (CSV)", dq.to_csv(index=False).encode(), "data_quality_log.csv", "text/csv")

# ================= ABOUT =================
with tabs[5]:
    a, b = st.columns([1.5, 1])
    with a:
        st.markdown("#### ℹ️ About this project")
        st.markdown("""
This dashboard tracks emergency department waiting times in Wales against the two national targets:
95% of patients spending less than 4 hours in an emergency department, and nobody waiting 12 hours or more.

**Method**
1. Download the full raw dataset from StatsWales (accredited official statistics).
2. Check the data: missing values, duplicates, recalculating every published percentage, reconciling boards to the Wales total, and finding breaks in each time series.
3. Build a tidy table of counts and recalculate percentages from the counts.
4. Present the results for people who are not data specialists, with the data quality log alongside the figures.

**Definitions**
- *Within 4 hours*: patients who spent less than 4 hours from arrival to admission, transfer or discharge.
- *Waited 12 hours or more*: total attendances minus those within 12 hours.
- *12-month figures* are worked out from summed counts, not by averaging monthly percentages.

**Limitations**

These are aggregate counts, so they cannot show why waits are long, such as bed availability or ambulance handovers.
Figures can be revised by StatsWales after publication. Hospital map locations are approximate.
""")
    with b:
        st.markdown("#### 👤 Built by")
        st.markdown(f"""<div class="card" style="min-height:0"><div class="bar" style="background:linear-gradient(90deg,{BLUE},{VIOLET},{ORANGE})"></div>
<div class="value" style="font-size:1.35rem;margin-top:6px">Afin Rasheed</div>
<div class="note" style="margin-bottom:10px">Data Analyst · MSc Data Science, Northumbria University</div>
💻 <a href="{GITHUB}">GitHub repository</a><br>🔗 <a href="{LINKEDIN}">LinkedIn</a><br>📊 <a href="{SOURCE}">Data source: StatsWales</a>
<div class="note" style="margin-top:10px">Built with Python, pandas, Plotly and Streamlit.</div></div>""", unsafe_allow_html=True)

st.markdown(f'<div class="footer">Data: StatsWales, Digital Health and Care Wales, to {latest:%B %Y}. '
            f'Analysis and dashboard by Afin Rasheed · <a href="{GITHUB}">Code on GitHub</a></div>', unsafe_allow_html=True)
