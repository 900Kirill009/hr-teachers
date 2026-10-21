from dash import Dash, html, dcc

from tabs import director, city


app = Dash(__name__)

app.layout = [
    html.H1("СППР 'Движуха в кадрах'"),
    dcc.Tabs([
        dcc.Tab(label="Директор школы", children=director.layout),
        dcc.Tab(label="Городской уровень", children=city.layout),
    ])
]


if __name__ == '__main__':
    app.run(debug=True)
