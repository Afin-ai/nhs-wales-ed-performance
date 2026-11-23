# NHS Wales Emergency Department Performance

An analysis of how Welsh health boards perform against the emergency department waiting time targets, with a focus on data quality.

**Author:** Afin Rasheed, MSc Data Science (Northumbria University)

## The question

How are Welsh health boards doing against the 4-hour and 12-hour targets, and how far can the published data be trusted for comparison?

## Data

StatsWales, *Emergency departments: performance against waiting times targets, October 2009 onwards*. Accredited official statistics from Digital Health and Care Wales.
https://stats.gov.wales/en-GB/3ce1cc28-0625-4674-89d6-9cf3a56f2d9c/start

Targets in Wales: 95% of patients spend less than 4 hours in an emergency department, and no one waits 12 hours or more.

## Headline findings (data to October 2026)

- In October 2026, 61.1% of patients in Wales were seen within 4 hours against a 95% target. That is the lowest month since April 2019, down from 66.0% a year earlier and 75.3% in October 2019.
- 131,500 patients waited 12 hours or more in the last 12 months, up 8% on the previous year. October 2026 alone had 11,830, more than double October 2019.
- Of the boards with a major ED, Aneurin Bevan had the best 12-month figure (72.5%) and Betsi Cadwaladr the lowest (56.4%), with 18.1% of its patients waiting 12 hours or more.
- Board totals hide big gaps between hospitals. The Grange, Aneurin Bevan's major ED, managed 45.6%. Ysbyty Glan Clwyd managed 33.2%, with 29.0% waiting 12 hours or more. Bronglais was best at 64.8%.

## Data quality findings

- All 26,736 published percentages match a recalculation from the counts.
- Health board changes in April 2019 (Abertawe Bro Morgannwg became Swansea Bay, Cwm Taf became Cwm Taf Morgannwg) break the trend for those boards.
- Nevill Hall and Royal Gwent stopped reporting as major EDs after December 2020 when The Grange University Hospital opened in November 2020. Both reappear as minor units from January 2021.
- Singleton minor unit stopped reporting after November 2018.
- Health boards add up exactly to the Wales total in every month.
- Minor injury units are only included from April 2012.
- Powys has no major ED, so its 100% figure is not comparable with other boards and is excluded from rankings.

The full log is produced by the notebook in `data/processed/data_quality_log.csv` and shown in the dashboard.

## Project structure

```
data/raw/          StatsWales download (not edited, not stored in the repo)
data/processed/    cleaned table and data quality log
notebooks/         01_load_check_clean.ipynb
app.py             Streamlit dashboard
ed_pipeline.py     the same cleaning steps as a module, used by the dashboard
```

## How to run

```
pip3 install -r requirements.txt
```

Download the data from StatsWales (View the full dataset, Download data, CSV), save it in `data/raw/`, then open the notebook and Run All.

Then start the dashboard. If there is no cleaned data in `data/processed`, it downloads the latest file from StatsWales and runs the same checks itself:

```
streamlit run app.py
```

## Tools

Python, pandas, Plotly, Streamlit, Jupyter.
