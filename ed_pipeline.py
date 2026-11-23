"""Load, check and clean the StatsWales emergency department dataset.
Used by app.py so the dashboard can rebuild the data straight from StatsWales.
The notebook walks through the same steps one at a time.
"""
import io
import pandas as pd
import requests

DATASET = "3ce1cc28-0625-4674-89d6-9cf3a56f2d9c"
URL = f"https://stats.gov.wales/en-GB/{DATASET}/download"
MEASURES = {
    "Total attendances": "total",
    "Attendances where patients spend less than the target time in an emergency department": "within",
    "Percentage of patients who spend less than the target time in an emergency department": "pct",
}


def download_raw():
    """Download the full raw CSV from StatsWales."""
    form = {"view_type": "unfiltered", "format": "csv", "view_choice": "raw", "extended": "yes",
            "download_language": "en-GB", "selected_filter_options": "[]", "action": "download"}
    r = requests.post(URL, data=form, timeout=120)
    r.raise_for_status()
    return pd.read_csv(io.BytesIO(r.content))


def clean(raw):
    """Return (tidy table, data quality log) from the raw StatsWales file."""
    log = []
    add = lambda check, finding, action: log.append({"check": check, "finding": finding, "action": action})

    df = raw.rename(columns={
        "Data values": "value", "Data description": "measure", "Date_reference": "month_ref",
        "Hospital": "area", "Hospital_reference": "area_code", "Hospital_hierarchy": "parent_code",
        "Hospital Type_reference": "unit_type", "Target": "target",
    })[["value", "measure", "month_ref", "area", "area_code", "parent_code", "unit_type", "target"]]
    df["parent_code"] = df["parent_code"].fillna("")
    df["month"] = pd.to_datetime(df["month_ref"].str.replace("m", "-") + "-01")
    df["measure"] = df["measure"].map(MEASURES)
    df["level"] = "Hospital"
    df.loc[df.parent_code == "XXXW92000004", "level"] = "Health board"
    df.loc[df.area == "Wales", "level"] = "Wales"

    bad = pd.to_numeric(df["value"], errors="coerce").isna().sum()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    add("Missing or non-numeric values", f"{bad} found", "No action needed" if bad == 0 else "Excluded")

    key = ["month_ref", "area_code", "unit_type", "measure", "target"]
    dupes = df.duplicated(key).sum()
    df = df.drop_duplicates(key)
    add("Duplicates", f"{dupes} duplicate rows", "No action needed" if dupes == 0 else "Kept first")

    idx = ["month_ref", "area_code", "unit_type"]
    tot = df[df.measure == "total"].set_index(idx)["value"].rename("total")
    chk = (df[df.measure == "within"].set_index(idx + ["target"])["value"].rename("within").to_frame()
           .join(df[df.measure == "pct"].set_index(idx + ["target"])["value"].rename("pct"))
           .reset_index().merge(tot.reset_index(), on=idx))
    gap = (100 * chk.within / chk.total - chk.pct).abs()
    add("Recalculated percentages", f"{len(chk):,} checked, {(gap > 0.05).sum()} differ by more than 0.05 points",
        "Percentages recalculated from counts")

    latest, earliest = df.month.max(), df.month.min()
    span = df.groupby(["area", "unit_type"])["month"].agg(["min", "max"]).reset_index()
    for _, r in span.iterrows():
        if r["max"] < latest:
            add("Series ends", f"{r.area} ({r.unit_type}) stops after {r['max']:%b %Y}",
                "Kept history, excluded from current comparisons")
        if r["min"] > earliest:
            add("Series starts", f"{r.area} ({r.unit_type}) starts {r['min']:%b %Y}",
                "Trends for this area start here")

    types = df[df.level == "Health board"].groupby("area")["unit_type"].unique()
    for b, t in types.items():
        if "Major" not in t:
            add("No major ED", f"{b} only has minor injury units", "Excluded from board rankings")

    t_all = df[(df.measure == "total") & (df.unit_type == "All")]
    diff = (t_all[t_all.level == "Wales"].set_index("month_ref")["value"]
            - t_all[t_all.level == "Health board"].groupby("month_ref")["value"].sum()).abs().max()
    add("Boards add up to Wales", f"Largest monthly gap: {diff:,.0f} attendances",
        "No action needed" if diff == 0 else "Investigate")

    w = df[df.measure.isin(["total", "within"])].copy()
    w["col"] = "total"
    w.loc[w.measure == "within", "col"] = "within_" + w.target.str.split().str[0] + "h"
    tidy = (w.pivot_table(index=["month", "area", "area_code", "parent_code", "level", "unit_type"],
                          columns="col", values="value", aggfunc="first").reset_index())
    tidy.columns.name = None
    tidy["pct_4h"] = 100 * tidy.within_4h / tidy.total
    tidy["pct_12h_or_less"] = 100 * tidy.within_12h / tidy.total
    tidy["over_12h"] = tidy.total - tidy.within_12h
    return tidy.sort_values(["month", "level", "area"]), pd.DataFrame(log)
