# data.py
import pandas as pd
import os

def load_data():
    path = os.path.join(os.path.dirname(__file__), 'data', 'teachers.parquet')
    df = pd.read_parquet(path)
    return df

# Глобальные справочники для фильтров
DF = load_data()
SCHOOLS = sorted(DF['school_num'].unique())
DISTRICTS = sorted(DF['district'].dropna().unique())
POSITIONS = sorted(DF['main_position_cat'].unique())