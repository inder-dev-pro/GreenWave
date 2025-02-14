import streamlit as st
import pandas as pd
import changefinder
from scipy import stats

# Load custom CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Function to detect appliance faults
def detect_appliance_fault(col, df, _r=0.01, _order=1, _smooth=10):
    df = df.copy()
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time')

    cf = changefinder.ChangeFinder(r=_r, order=_order, smooth=_smooth)
    
    ch_df = pd.DataFrame()
    ch_df[col] = df[col].resample('D').mean()
    ch_df = ch_df.dropna()

    ch_df['change_score'] = [cf.update(i) for i in ch_df[col]]

    ch_score_q1 = stats.scoreatpercentile(ch_df['change_score'], 25)
    ch_score_q3 = stats.scoreatpercentile(ch_df['change_score'], 75)
    iqr = ch_score_q3 - ch_score_q1

    thr_upper = ch_score_q3 + (iqr * 3)
    thr_lower = ch_score_q1 - (iqr * 3)

    if ch_df['change_score'].iloc[-1] > thr_upper:
        return f"⚠️ Overconsumption Issue in {col}!"
    elif ch_df['change_score'].iloc[-1] < thr_lower:
        return f"❌ Possible Malfunction in {col}!"
    return None

# Streamlit UI
st.set_page_config(page_title="GreenWave Appliance Fault Detector", layout="wide")

st.markdown("<h1 class='title'>🔍 GreenWave Appliance Fault Detector</h1>", unsafe_allow_html=True)
st.markdown("<p class='description'>Upload your smart home dataset to detect faulty appliances based on power consumption patterns.</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 Upload CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, low_memory=False)
    df.columns = [col.replace(' [kW]', '') for col in df.columns]

    # Clean and preprocess data
    df['Furnace'] = df[['Furnace 1', 'Furnace 2']].sum(axis=1)
    df['Kitchen'] = df[['Kitchen 12', 'Kitchen 14', 'Kitchen 38']].sum(axis=1)
    df.drop(['Furnace 1', 'Furnace 2', 'Kitchen 12', 'Kitchen 14', 'Kitchen 38'], axis=1, inplace=True)

    df['time'] = pd.to_datetime(df['time'], unit='s')

    # Run fault detection with progress bar
    st.subheader("🔬 Detecting Appliance Faults...")
    progress = st.progress(0)

    faults = []
    total_cols = len(df.columns[1:])
    
    for idx, col in enumerate(df.columns[1:]):  # Skip time column
        fault = detect_appliance_fault(col, df)
        if fault:
            faults.append(fault)
        
        progress.progress((idx + 1) / total_cols)

    progress.empty()  # Remove progress bar after completion

    # Display results
    if faults:
        st.subheader("🚨 Faults Detected")
        for fault in faults:
            st.markdown(f"<div class='fault-card'>{fault}</div>", unsafe_allow_html=True)
    else:
        st.success("✅ All appliances are functioning normally.")

st.markdown("<p class='footer'>Developed with ❤️ by GreenWave</p>", unsafe_allow_html=True)
