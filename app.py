import streamlit as st
import yfinance as yf
import pandas as pd
import time
import plotly.graph_objects as go

st.set_page_config(page_title="Futures vs Spot Gap", layout="wide")

st.title("📈 Live Futures vs Spot Gap Dashboard")

# ─── ASSET CONFIG ───
data = [
    ("Gold", "GC=F", "GLD"),  # SPDR Gold Shares ETF as spot proxy
    ("XAUUSD", "XAUUSD=X", "XAUUSD=X"),  # Gold/USD Forex pair
    ("Silver", "SI=F", "SLV"),  # iShares Silver Trust ETF as spot proxy
    ("NAS100", "NQ=F", "^NDX"),
    ("US30", "YM=F", "^DJI"),
    ("SPX500", "ES=F", "^GSPC"),
    ("Oil (WTI)", "CL=F", "USO"),  # United States Oil Fund as spot proxy
    ("Gas (Natural)", "NG=F", "UNG")  # United States Natural Gas Fund as spot proxy
]

# Display last update time
st.write(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# ─── FETCH AND DISPLAY DATA ───
rows = []
charts = []

for name, fut_symbol, spot_symbol in data:
    try:
        futures = yf.Ticker(fut_symbol).history(period="5d")["Close"]
        spot = yf.Ticker(spot_symbol).history(period="5d")["Close"]

        # Skip if no data available
        if futures.empty or spot.empty:
            rows.append([name, "N/A", "N/A", "N/A"])
            continue

        # Current values
        f_now = futures.iloc[-1]
        s_now = spot.iloc[-1]
        gap = f_now - s_now

        rows.append([name, f"${f_now:,.2f}", f"${s_now:,.2f}", f"{gap:+.2f}"])

        # Chart: Futures vs Spot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=futures.index, y=futures, mode="lines", name="Futures", line=dict(color="blue")))
        fig.add_trace(go.Scatter(x=spot.index, y=spot, mode="lines", name="Spot", line=dict(color="orange")))
        fig.update_layout(title=f"{name} (Futures vs Spot)", height=300, margin=dict(l=40, r=40, t=40, b=20))

        charts.append(fig)

    except Exception as e:
        # Handle any errors gracefully
        rows.append([name, "ERROR", "ERROR", "ERROR"])
        st.warning(f"Error fetching data for {name}: {str(e)}")

# Display table first
df = pd.DataFrame(rows, columns=["Asset", "Futures", "Spot", "Gap (Fut - Spot)"])
st.dataframe(df, use_container_width=True)

# Then display all charts
for fig in charts:
    st.plotly_chart(fig, use_container_width=True)

# Auto-refresh every 1 second
time.sleep(1)
st.rerun()