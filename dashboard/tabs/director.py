from dash import html, dcc

import charts as ch
from data import DF, YEARS

# Пока без интерактива: статичный рендер для самой крупной школы за последний год.
# TODO: заменить на фильтры год/школа + callbacks (этап 2)
YEAR = YEARS[-1]
SCHOOL = int(DF[DF['year'] == YEAR]['school_num'].value_counts().index[0])


def _graph(fig):
    return dcc.Graph(figure=fig, config={'displayModeBar': False})


layout = html.Div([
    html.H3(f"Школа № {SCHOOL}, {YEAR} год"),
    _graph(ch.fig_gaps_vs_moscow(DF, YEAR, SCHOOL)),
    _graph(ch.fig_age_school_vs_moscow(DF, YEAR, SCHOOL)),
    _graph(ch.fig_qualification_categories(DF, YEAR, SCHOOL)),
    _graph(ch.fig_education_profdev(DF, YEAR, SCHOOL)),
    _graph(ch.fig_teachers_by_subject(DF, YEAR, school_num=SCHOOL)),
    _graph(ch.fig_dynamics_years(DF, school_num=SCHOOL)),
])
