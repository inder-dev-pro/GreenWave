import streamlit as st
import changefinder
from scipy import stats
import numpy as np
import pandas as pd

st.set_page_config(page_title="GreenWave Appliances")
st.title("GreenWave Appliances Fault Detector")

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
            return {"appliance": col, "status": "⚠️ Overconsumption Issue"}
        elif last_power < avg_power * 0.5:
            return {"appliance": col, "status": "❌ Possible Malfunction"}
        else:
            return {"appliance": col, "status": "✅ Normal"}
    return None

uploaded_file = st.file_uploader("Upload your CSV file", type=['csv'])

if uploaded_file is not None:
    with st.spinner('Analyzing appliances...'):
        df = pd.read_csv(uploaded_file, low_memory=False)
        df = preprocess_data(df)
        
        if df is not None:
            # Get all numeric columns except 'time'
            appliance_cols=df.columns[2:10]
            
            # Check all appliances and show only those with issues
            st.subheader("Detected Issues:")
            issues_found = False
            
            for appliance in appliance_cols:
                result = detect_appliance_fault(appliance, df)
                if result:  # Only show appliances with issues
                    issues_found = True
                    st.write(f"{result['appliance']}: {result['status']}")
                else:
                    st.write(f"{appliance}: ✅ Normal")
            
            if not issues_found:
                st.success("No issues detected in any appliances.")

else:
    st.info("Upload a CSV file to check for appliance faults")