import streamlit as st
import yfinance as yf
import pandas as pd
import time
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="Futures vs Spot Gap", layout="wide")

# Get API key from Streamlit secrets or environment
TWELVE_DATA_API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", "demo")  # 'demo' for testing

# Cache for gold spot price (refresh every 10 seconds to avoid rate limits)
if 'gold_spot_cache' not in st.session_state:
    st.session_state.gold_spot_cache = None
    st.session_state.gold_spot_timestamp = 0

def get_gold_spot_price():
    """Fetch real-time gold spot price from Twelve Data API with caching"""
    current_time = time.time()

    # Use cached value if less than 10 seconds old
    if (st.session_state.gold_spot_cache is not None and
        current_time - st.session_state.gold_spot_timestamp < 10):
        return st.session_state.gold_spot_cache

    # Fetch new price from API
    try:
        url = f"https://api.twelvedata.com/price?symbol=XAUUSD&apikey={TWELVE_DATA_API_KEY}"
        response = requests.get(url, timeout=5)
        data = response.json()

        # Check for API errors
        if 'code' in data and data['code'] == 403:
            st.error("⚠️ API Key Error! Please add your Twelve Data API key to Streamlit Secrets")
            return st.session_state.gold_spot_cache  # Return cached value if available
        if 'message' in data:
            # Don't show rate limit warnings, just use cache
            if 'run out of API credits' not in data.get('message', ''):
                st.warning(f"API Message: {data['message']}")
            return st.session_state.gold_spot_cache  # Return cached value
        if 'price' in data:
            price = float(data['price'])
            # Update cache
            st.session_state.gold_spot_cache = price
            st.session_state.gold_spot_timestamp = current_time
            return price
        return st.session_state.gold_spot_cache
    except Exception as e:
        st.error(f"Gold API Error: {str(e)}")
        return st.session_state.gold_spot_cache

st.title("📈 Live Futures vs Spot Gap Dashboard")

# ─── ASSET CONFIG ───
data = [
    ("Gold", "GC=F", "API", 1),  # Gold Futures vs Real Spot from API
    ("Silver", "SI=F", "SLV", 1),  # iShares Silver Trust ETF as spot proxy
    ("NAS100", "NQ=F", "^NDX", 1),
    ("US30", "YM=F", "^DJI", 1),
    ("SPX500", "ES=F", "^GSPC", 1),
    ("Oil (WTI)", "CL=F", "USO", 1),  # United States Oil Fund as spot proxy
    ("Gas (Natural)", "NG=F", "UNG", 1)  # United States Natural Gas Fund as spot proxy
]

# Display last update time
st.write(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# ─── FETCH AND DISPLAY DATA ───
rows = []
charts = []

for name, fut_symbol, spot_symbol, multiplier in data:
    try:
        futures = yf.Ticker(fut_symbol).history(period="5d")["Close"]

        # Handle Gold with real-time API spot price
        if spot_symbol == "API":
            if futures.empty:
                rows.append([name, "N/A", "N/A", "N/A"])
                continue

            # Get real-time gold spot price from API
            gold_spot = get_gold_spot_price()
            if gold_spot is None:
                rows.append([name, f"${futures.iloc[-1]:,.2f}", "API Error", "N/A"])
                continue

            # Current values
            f_now = futures.iloc[-1]
            s_now = gold_spot
            gap = f_now - s_now

            rows.append([name, f"${f_now:,.2f}", f"${s_now:,.2f}", f"{gap:+.2f}"])

            # Chart: For gold, create synthetic spot history using current spot price
            spot = pd.Series([gold_spot] * len(futures), index=futures.index)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=futures.index, y=futures, mode="lines", name="Futures", line=dict(color="blue")))
            fig.add_trace(go.Scatter(x=spot.index, y=spot, mode="lines", name="Real Spot (Live)", line=dict(color="orange", dash="dash")))
            fig.update_layout(title=f"{name} (Futures vs Real Spot)", height=300, margin=dict(l=40, r=40, t=40, b=20))
            charts.append(fig)
        else:
            # Regular Yahoo Finance spot data
            spot_raw = yf.Ticker(spot_symbol).history(period="5d")["Close"]

            # Skip if no data available
            if futures.empty or spot_raw.empty:
                rows.append([name, "N/A", "N/A", "N/A"])
                continue

            # Apply multiplier to spot price
            spot = spot_raw * multiplier

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