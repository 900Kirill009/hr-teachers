import pandas as pd

teachers = pd.read_parquet("../data/teachers_clean.parquet")



# Списки для фильтров, добавлять новые по мере необходимости
YEARS = sorted(teachers["year"].unique())
SCHOOLS = sorted(teachers["school_num"].unique())

