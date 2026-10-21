from dash import html, dcc

from data import YEARS


def year_filter(prefix):
    return html.Div(
        [
            html.Label("Год"),
            dcc.Dropdown(
                id=prefix + '-year',
                options=YEARS,
                value=YEARS[-1],
                clearable=False


            ),
        ]
    )