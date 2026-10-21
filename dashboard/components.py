"""Переиспользуемые элементы разметки: карточки, KPI, плитки округов, таблица."""
from __future__ import annotations

import math

import pandas as pd
from dash import html, dcc, dash_table

import charts as ch
import metrics as mt

TILE_COLORS = ['#dfe8f2', '#a9c1df', '#f0b98d', '#b5490f']
TILE_TEXT   = [ch.INK, ch.INK, ch.INK, 'white']
TILE_LEGEND = ['ниже на 1,5+ п.п.', 'немного ниже', 'выше среднего', 'выше на 2,5+ п.п.']


def fmt(v, digits=1, suffix='') -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return '—'
    s = f'{v:,.{digits}f}'.replace(',', ' ').replace('.', ',')
    return s + suffix


def _legend(fig):
    """Легенда в HTML: Plotly переносит длинные русские подписи по одной в строку."""
    items, seen = [], set()
    for t in fig.data:
        color = getattr(getattr(t, 'marker', None), 'color', None)
        if not t.name or t.showlegend is False or not isinstance(color, str) or t.name in seen:
            continue
        seen.add(t.name)
        items.append(html.Span([html.Span(className='swatch', style={'background': color}),
                                t.name], className='legend-item'))
    return html.Div(items, className='legend') if items else None


def graph(fig, height=360, gid=None):
    """Карточка с графиком: заголовок, подзаголовок и легенда — в HTML, не в Plotly."""
    props = {'id': gid} if gid else {}
    meta = fig.layout.meta or {}
    header = []
    if meta.get('title'):
        header = [html.Div(meta['title'], className='card-title')]
        if meta.get('subtitle'):
            header.append(html.Div(meta['subtitle'], className='card-sub'))
        legend = _legend(fig) if meta.get('legend') else None
        if legend:
            header.append(legend)
        fig.update_layout(title=None, showlegend=False, margin=dict(t=8))
        height -= (44 if meta.get('subtitle') else 24) + (24 if legend else 0)
    return html.Div(header + [dcc.Graph(figure=fig, config={'displayModeBar': False},
                                        responsive=True, style={'height': f'{height}px'},
                                        **props)], className='card')


def kpi(title, value, sub=None, accent=None, compare=None):
    """KPI-карточка. compare — список пар (подпись, значение) справа."""
    body = [html.Div(title, className='kpi-title'),
            html.Div(value, className='kpi-value' + (f' kpi-{accent}' if accent else ''))]
    if sub:
        body.append(html.Div(sub, className='kpi-sub'))
    children = [html.Div(body, className='kpi-main')]
    if compare:
        children.append(html.Div([html.Div([html.Span(l + ' '), html.B(v)])
                                  for l, v in compare], className='kpi-compare'))
    return html.Div(children, className='card kpi' + (' kpi-wide' if compare else ''))


def kpi_row(cards, cols=None):
    return html.Div(cards, className='kpi-row',
                    style={'gridTemplateColumns': f'repeat({cols or len(cards)}, minmax(0, 1fr))'})


def note(text):
    return html.Div(text, className='note')


def district_tiles(df: pd.DataFrame, year: int, selected: str | None):
    table, city, name = mt.district_tiles(df, year)
    tiles = []
    for r in table.itertuples():
        lvl = mt.tile_level(r.delta)
        tiles.append(html.Button(
            [html.Div(r.district, className='tile-name'), html.Div(fmt(r.value, 1, '%'))],
            id={'type': 'district-tile', 'index': r.district}, n_clicks=0,
            className='tile' + (' tile-selected' if r.district == selected else ''),
            style={'background': TILE_COLORS[lvl], 'color': TILE_TEXT[lvl]},
            title=f'{r.district}: {fmt(r.value, 1, "%")} ({fmt(r.delta, 1, " п.п.")} к Москве)'))
    legend = html.Div(
        [html.Div('Относительно Москвы', className='legend-title')] +
        [html.Div([html.Span(className='swatch', style={'background': c}), t])
         for c, t in zip(TILE_COLORS, TILE_LEGEND)] +
        [html.Div('Клик по округу — фильтр по округу на всех вкладках', className='hint')],
        className='tile-legend')
    return html.Div([
        html.Div(name, className='card-title'),
        html.Div(f'Доля педагогов · среднее по Москве {fmt(city, 1, "%")}', className='card-sub'),
        html.Div([html.Div(tiles, className='tiles'), legend], className='tiles-wrap'),
    ], className='card')


def data_table(df: pd.DataFrame, title, subtitle, tid):
    return html.Div([
        html.Div(title, className='card-title'),
        html.Div(subtitle, className='card-sub'),
        dash_table.DataTable(
            id=tid, data=df.to_dict('records'),
            columns=[{'name': c, 'id': c} for c in df.columns],
            sort_action='native', page_size=12,
            style_as_list_view=True,
            style_table={'overflowX': 'auto'},
            style_header={'fontWeight': 600, 'backgroundColor': 'transparent',
                          'whiteSpace': 'normal', 'height': 'auto',
                          'borderBottom': f'1px solid {ch.INK}', 'color': ch.MUTED},
            style_cell={'fontFamily': ch.FONT, 'fontSize': 13, 'padding': '8px 10px',
                        'backgroundColor': 'transparent', 'color': ch.INK,
                        'border': 'none', 'borderBottom': '1px solid #e6e3de'},
            style_cell_conditional=[{'if': {'column_id': df.columns[0]}, 'textAlign': 'left'}],
        ) if len(df) else html.Div('Нет данных для выбранных фильтров', className='empty'),
    ], className='card')
