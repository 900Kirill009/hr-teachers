from dash import html, dcc
from dashboard.charts import get_age_structure_fig
from dashboard.data import load_data # ваша функция из data.py

df = load_data() # Загружается один раз при старте

# Тестовый вызов без интерактива (статичный рендер)
layout = html.Div([
    html.H3("Анализ школы (Тест)"),
    dcc.Graph(
        id='age-structure-graph',
        figure=get_age_structure_fig(df, school_num=478, year=2023)
    )
])