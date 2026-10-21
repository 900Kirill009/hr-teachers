from dash import Dash, html, dcc


app = Dash(__name__)

app.layout = [
    html.H1("СППР 'Движуха в кадрах'"),
    dcc.Tabs([
        dcc.Tab(label="Директор школы"), #TODO: Заменить на  children=director.layout
        dcc.Tab(label="Городской уровень") #TODO: Заменить на children=city.layout
    ])
]






if __name__ == '__main__':
    app.run(debug=True)