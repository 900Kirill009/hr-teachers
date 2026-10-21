# data.py
import pandas as pd
import os

# Данные лежат в корневой папке data/ (на уровень выше dashboard/)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


def load_data():
    path = os.path.join(DATA_DIR, 'teachers.parquet')
    df = pd.read_parquet(path)
    return df

# Глобальные справочники для фильтров
DF = load_data()
YEARS = sorted(int(y) for y in DF['year'].unique())
SCHOOLS = sorted(int(s) for s in DF['school_num'].unique())
DISTRICTS = sorted(DF['district'].dropna().unique())
POSITIONS = sorted(DF['main_position_cat'].unique())
SUBJECTS = sorted(s for s in DF['speciality'].dropna().unique() if s != 'не указано')
