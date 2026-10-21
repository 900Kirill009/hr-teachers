from dash import html, dcc

import charts as ch
from data import DF, YEARS

# Пока без интерактива: статичный рендер по всей Москве.
# TODO: заменить на фильтры год/округ + callbacks (этап 2)
YEAR = YEARS[-1]
# Исходы (ушёл/перешёл) известны только для годов, после которых есть данные
MOBILITY_YEAR = int(DF.loc[DF['target'].notna(), 'year'].max())


def _graph(fig):
    return dcc.Graph(figure=fig, config={'displayModeBar': False})


layout = html.Div([
    html.H3(f"Москва, {YEAR} год"),
    _graph(ch.fig_age_moscow(DF, YEAR)),
    _graph(ch.fig_teachers_by_subject(DF, YEAR)),
    _graph(ch.fig_mobility_actual(DF, year=MOBILITY_YEAR)),
    _graph(ch.fig_dynamics_years(DF)),
])
