# -*- coding: utf-8 -*-
"""GreenWaveAppliances.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1j6wm2JG938rd-upQwoabYATnSu4xbOKA

```
This is to install the necessary modules anf functions!
```
"""

import kagglehub
taranvee_smart_home_dataset_with_weather_information_path = kagglehub.dataset_download('taranvee/smart-home-dataset-with-weather-information')
taranvee_smart_home_dataset_with_weather_information_path
print('Data source import complete.')

import os
!pip install changefinder
import changefinder
from scipy import stats
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import grangercausalitytests
from statsmodels.tsa.stattools import adfuller
import numpy as np
import pandas as pd

for dirname, _, filenames in os.walk('/kaggle/input'):
    for filename in filenames:
        print(os.path.join(dirname, filename))

df = pd.read_csv(r"/root/.cache/kagglehub/datasets/taranvee/smart-home-dataset-with-weather-information/versions/1/HomeC.csv",low_memory=False)
print(f'HomeC.csv : {df.shape}')
df.head(3)

df.columns
df.info()

df.columns = [i.replace(' [kW]', '') for i in df.columns]

df['Furnace'] = df[['Furnace 1','Furnace 2']].sum(axis=1)
df['Kitchen'] = df[['Kitchen 12','Kitchen 14','Kitchen 38']].sum(axis=1)
df.drop(['Furnace 1','Furnace 2','Kitchen 12','Kitchen 14','Kitchen 38','icon','summary'], axis=1, inplace=True)

df[df.isnull().any(axis=1)]

df = df[0:-1]

df.columns

df['cloudCover'].unique()

df[df['cloudCover']=='cloudCover'].shape

df['cloudCover'].replace(['cloudCover'], method='bfill', inplace=True)
df['cloudCover'] = df['cloudCover'].astype('float')

pd.to_datetime(df['time'], unit='s').head(3)

df['time'] = pd.DatetimeIndex(pd.date_range('2016-01-01 05:00', periods=len(df),  freq='min'))
df.head(3)

df['year'] = df['time'].apply(lambda x : x.year)
df['month'] = df['time'].apply(lambda x : x.month)
df['day'] = df['time'].apply(lambda x : x.day)
df['weekday'] = df['time'].apply(lambda x : x.day_name())
df['weekofyear'] = df['time'].apply(lambda x : x.weekofyear)
df['hour'] = df['time'].apply(lambda x : x.hour)
df['minute'] = df['time'].apply(lambda x : x.minute)
df.head(3)

def hours2timing(x):
    if x in [22,23,0,1,2,3]:
        timing = 'Night'
    elif x in range(4, 12):
        timing = 'Morning'
    elif x in range(12, 17):
        timing = 'Afternoon'
    elif x in range(17, 22):
        timing = 'Evening'
    else:
        timing = 'X'
    return timing

df['timing'] = df['hour'].apply(hours2timing)
df.head(3)

df['use_HO'] = df['use']
df['gen_Sol'] = df['gen']
df.drop(['use','House overall','gen','Solar'], axis=1, inplace=True)
df.head(3)

"""

```
Detecting flaws in appliances on the basis of power consumption
```

"""

def detect_appliance_fault(col, df, _r=0.01, _order=1, _smooth=10):
    df = df.copy()  # Avoid modifying original DataFrame
    df['time'] = pd.to_datetime(df['time'])  # Ensure 'time' is datetime
    df = df.set_index('time')  # Set datetime as index

    cf = changefinder.ChangeFinder(r=_r, order=_order, smooth=_smooth)

    # Resample data to daily frequency
    ch_df = pd.DataFrame()
    ch_df[col] = df[col].resample('D').mean()

    # Remove NaN values after resampling
    ch_df = ch_df.dropna()

    # Compute change scores
    ch_df['change_score'] = [cf.update(i) for i in ch_df[col]]

    # Compute thresholds using IQR method
    ch_score_q1 = stats.scoreatpercentile(ch_df['change_score'], 25)
    ch_score_q3 = stats.scoreatpercentile(ch_df['change_score'], 75)
    iqr = ch_score_q3 - ch_score_q1

    thr_upper = ch_score_q3 + (iqr * 3)  # Detect high spikes
    thr_lower = ch_score_q1 - (iqr * 3)  # Detect sudden drops

    # Identify timestamps where abrupt changes occur
    high_spikes = ch_df[ch_df['change_score'] > thr_upper].index.tolist()
    low_drops = ch_df[ch_df['change_score'] < thr_lower].index.tolist()

    # Classify fault type
    if high_spikes or low_drops:
        avg_power = ch_df[col].mean()
        last_power = ch_df[col].iloc[-1]

        if last_power > avg_power * 1.5:
            status = "⚠️ Overconsumption Issue – Possible Fault!"
            return {
              "appliance": col,
              "status": status
        }
        elif last_power < avg_power * 0.5:
            status = "❌ Possible Malfunction – Underperforming or Disconnected!"
            return {
              "appliance": col,
              "status": status
        }
    else:
        return None

faulty_appliances = []

for i in range(1, 10):  # Ensure valid index range
    col_name = df.columns[i]
    fault_info = detect_appliance_fault(col_name, df)

    if fault_info:
        print(f"🚨 Fault Detected in {fault_info['appliance']}!")
        print(f"🔴 Status: {fault_info['status']}\n")
        faulty_appliances.append(fault_info)
    else:
        print(f"✅ {col_name} is functioning normally.\n")