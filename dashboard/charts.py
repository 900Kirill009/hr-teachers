import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Задаем жесткий порядок для возрастных групп, чтобы ось X всегда была логичной
AGE_GROUPS_ORDER = ['до 25', '25–34', '35–44', '45–54', '55–64', '65+']

def get_age_structure_fig(df: pd.DataFrame, school_num: int, year: int) -> go.Figure:
    """
    Строит гистограмму распределения педагогов по возрастным группам.
    """
    # 1. Фильтрация
    mask = (df['year'] == year) & (df['school_num'] == school_num)
    filtered_df = df[mask]
    
    # 2. Защита от пустых данных
    if filtered_df.empty:
        return go.Figure().update_layout(
            title=f"Школа № {school_num} ({year}): Нет данных",
            xaxis={"visible": False}, yaxis={"visible": False},
            annotations=[{
                "text": "Педагоги не найдены",
                "xref": "paper", "yref": "paper",
                "showarrow": False, "font": {"size": 20}
            }]
        )

    # 3. Агрегация с сохранением порядка
    age_counts = (
        filtered_df['age_group']
        .value_counts()
        .reindex(AGE_GROUPS_ORDER, fill_value=0)
        .reset_index()
    )
    age_counts.columns = ['Возрастная группа', 'Количество']

    # 4. Построение
    fig = px.bar(
        age_counts,
        x='Возрастная группа',
        y='Количество',
        title=f'Возрастная структура: Школа № {school_num} ({year})',
        color='Количество',
        color_continuous_scale='blues',
        category_orders={'Возрастная группа': AGE_GROUPS_ORDER}
    )
    fig.update_layout(template='plotly_white', margin=dict(t=50, b=20, l=20, r=20))
    return fig