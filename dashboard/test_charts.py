import pandas as pd
from charts import get_age_structure_fig # импортируем вашу функцию

# 1. Загружаем данные напрямую (минуя data.py, если он тоже не готов)
df = pd.read_parquet("data/teachers_clean.parquet") 

# 2. Берем тестовые параметры (например, самая частая школа за последний год)
test_year = df['year'].max()
test_school = df[df['year'] == test_year]['school_num'].value_counts().index[0]

print(f"🔍 Тестируем: Школа №{test_school}, {test_year} год")

# 3. Вызываем функцию построения графика
fig = get_age_structure_fig(df, school_num=test_school, year=test_year)

# 4. Открываем график в браузере одним кликом
fig.show() 