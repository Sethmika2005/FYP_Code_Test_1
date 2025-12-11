# streamlit_app.py
# Run: streamlit run streamlit_app.py
# pip install streamlit yfinance pandas

import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Price & Financials", layout="wide")

st.title("Price & Financials (Ticker-driven)")

ticker = st.text_input("Ticker (use exchange suffix if needed, e.g., LSEG.L)", value="LSEG.L").strip()

@st.cache_data(ttl=3600)
def load_data(tkr: str):
    t = yf.Ticker(tkr)

    # --- Meta / names ---
    name = None
    try:
        # get_info is slower but has longName for most tickers
        info = t.get_info() or {}
        name = info.get("longName") or info.get("shortName")
    except Exception:
        name = None

    # --- Price history (5 years daily close, auto-adjusted) ---
    hist = t.history(period="5y", interval="1d", auto_adjust=True)
    if not hist.empty:
        hist = hist[["Close"]].copy()

    # --- Annual financial statements (latest column only) ---
    income_a = t.income_stmt
    balance_a = t.balance_sheet
    cashflow_a = t.cashflow

    def latest_col(df: pd.DataFrame):
        if df is None or df.empty:
            return None, None
        # yfinance usually returns most recent period in the first column
        col = df.columns[0]
        # turn into a 2-col table: Item | Value (for the most recent year)
        out = df[[col]].reset_index()
        out.columns = ["Item", "Value"]
        return out, col

    inc_latest, inc_col = latest_col(income_a)
    bal_latest, bal_col = latest_col(balance_a)
    cf_latest, cf_col = latest_col(cashflow_a)

    # prettify period labels
    def pretty_period(col):
        if col is None: return "N/A"
        try:
            return pd.to_datetime(str(col)).strftime("%Y-%m-%d")
        except Exception:
            return str(col)

    return {
        "name": name,
        "hist": hist,
        "inc": inc_latest,
        "inc_period": pretty_period(inc_col),
        "bal": bal_latest,
        "bal_period": pretty_period(bal_col),
        "cf": cf_latest,
        "cf_period": pretty_period(cf_col),
    }

def format_commas(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    # format numeric 'Value' column with commas (keep non-numerics as-is)
    def fmt(x):
        try:
            if pd.isna(x): return ""
            return f"{float(x):,.0f}"
        except Exception:
            return x
    if "Value" in out.columns:
        out["Value"] = out["Value"].apply(fmt)
    return out

if ticker:
    with st.spinner("Loading…"):
        data = load_data(ticker)

    # Header: ticker + name
    left, right = st.columns([2, 3])
    with left:
        st.subheader(f"Ticker: **{ticker.upper()}**")
        st.caption(f"Instrument name: {data['name'] or 'N/A'}")

    # Price chart (5y)
    hist = data["hist"]
    if hist is None or hist.empty:
        st.error("No price history returned. Check the ticker or exchange suffix.")
    else:
        with right:
            last_dt = hist.index[-1]
            last_px = hist["Close"].iloc[-1]
            st.metric(label="Last Close (most recent obs.)", value=f"{last_px:,.2f}", help=str(last_dt.date()))

        st.subheader("5-Year Daily Close")
        st.line_chart(hist["Close"])

        # download CSV
        st.download_button(
            "Download 5y CSV",
            data=hist.to_csv(index=True).encode("utf-8"),
            file_name=f"{ticker.upper()}_5y_daily_close.csv",
            mime="text/csv",
        )

    # Financial statements (latest annual period)
    st.markdown("---")
    st.subheader("Latest Annual Financial Statements")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"**Income Statement**  \n_Period end: {data['inc_period']}_")
        if data["inc"] is None or data["inc"].empty:
            st.info("Not available.")
        else:
            st.dataframe(format_commas(data["inc"]), use_container_width=True)
            st.download_button(
                "Download Income Statement (latest year)",
                data=data["inc"].to_csv(index=False).encode("utf-8"),
                file_name=f"{ticker.upper()}_income_statement_latest_year.csv",
                mime="text/csv",
            )

    with c2:
        st.markdown(f"**Statement of Financial Position (Balance Sheet)**  \n_Period end: {data['bal_period']}_")
        if data["bal"] is None or data["bal"].empty:
            st.info("Not available.")
        else:
            st.dataframe(format_commas(data["bal"]), use_container_width=True)
            st.download_button(
                "Download Balance Sheet (latest year)",
                data=data["bal"].to_csv(index=False).encode("utf-8"),
                file_name=f"{ticker.upper()}_balance_sheet_latest_year.csv",
                mime="text/csv",
            )

    with c3:
        st.markdown(f"**Cash Flow Statement**  \n_Period end: {data['cf_period']}_")
        if data["cf"] is None or data["cf"].empty:
            st.info("Not available.")
        else:
            st.dataframe(format_commas(data["cf"]), use_container_width=True)
            st.download_button(
                "Download Cash Flow (latest year)",
                data=data["cf"].to_csv(index=False).encode("utf-8"),
                file_name=f"{ticker.upper()}_cashflow_latest_year.csv",
                mime="text/csv",
            )
else:
    st.info("Enter a ticker to load the chart and statements.")
