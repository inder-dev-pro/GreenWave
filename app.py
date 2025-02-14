import streamlit as st
import changefinder
from scipy import stats
import numpy as np
import pandas as pd

# Set page config
st.set_page_config(
    page_title="GreenWave Appliances",
    page_icon="🌿",
    layout="wide"
)

# Title and description
st.title("🌿 GreenWave Appliances")
st.markdown("Monitor and analyze smart home appliance power consumption with automatic fault detection.")

def preprocess_data(df):
    try:
        # Clean column names
        df.columns = [i.replace(' [kW]', '') for i in df.columns]
        
        # Combine related columns if they exist
        if all(col in df.columns for col in ['Furnace 1', 'Furnace 2']):
            df['Furnace'] = df[['Furnace 1','Furnace 2']].sum(axis=1)
            df.drop(['Furnace 1','Furnace 2'], axis=1, inplace=True)
            
        if all(col in df.columns for col in ['Kitchen 12', 'Kitchen 14', 'Kitchen 38']):
            df['Kitchen'] = df[['Kitchen 12','Kitchen 14','Kitchen 38']].sum(axis=1)
            df.drop(['Kitchen 12','Kitchen 14','Kitchen 38'], axis=1, inplace=True)
        
        # Process timestamp
        if 'time' not in df.columns:
            st.error("Error: The CSV file must contain a 'time' column.")
            return None
            
        # Convert time column to datetime
        df['time'] = pd.DatetimeIndex(pd.date_range('2016-01-01 05:00', periods=len(df),  freq='min'))
        
        return df
        
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return None

def detect_appliance_fault(col, df, _r=0.01, _order=1, _smooth=10):
    df = df.copy()
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

    high_spikes = ch_df[ch_df['change_score'] > thr_upper].index.tolist()
    low_drops = ch_df[ch_df['change_score'] < thr_lower].index.tolist()

    if high_spikes or low_drops:
        avg_power = ch_df[col].mean()
        last_power = ch_df[col].iloc[-1]

        if last_power > avg_power * 1.5:
            status = "⚠️ Overconsumption Issue – Possible Fault!"
            return {"appliance": col, "status": status, "data": ch_df}
        elif last_power < avg_power * 0.5:
            status = "❌ Possible Malfunction – Underperforming or Disconnected!"
            return {"appliance": col, "status": status, "data": ch_df}
    return {"appliance": col, "status": "✅ Functioning normally", "data": ch_df}

# File upload section
st.header("📤 Upload Data")
uploaded_file = st.file_uploader("Upload your CSV file", type=['csv'])

if uploaded_file is not None:
    # Load and preprocess data
    with st.spinner('Processing data...'):
        df = pd.read_csv(uploaded_file, low_memory=False)
        df = preprocess_data(df)
        
        if df is not None:
            st.success('Data processed successfully!')
            
            # Get numeric columns for appliance selection
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            appliance_cols = [col for col in numeric_cols if col != 'time']
            
            selected_appliances = st.multiselect(
                "Select Appliances to Monitor",
                options=appliance_cols,
                default=appliance_cols[:2] if len(appliance_cols) >= 2 else appliance_cols
            )

            if selected_appliances:
                # Main content area
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.header("📊 Current Consumption")
                    st.line_chart(df.set_index('time')[selected_appliances])

                with col2:
                    st.header("🔍 Fault Detection")
                    for appliance in selected_appliances:
                        result = detect_appliance_fault(appliance, df)
                        st.write(f"{appliance}: {result['status']}")

else:
    st.info("Please upload a CSV file to begin analysis. The file should contain:")
    st.markdown("""
    - A 'time' column with timestamps
    - Power consumption data columns (in kW)
    - Optional columns like 'Furnace 1', 'Furnace 2', etc.
    """)

# Footer
st.markdown("---")
st.markdown("Built with Streamlit by GreenWave Analytics Team 🌿")