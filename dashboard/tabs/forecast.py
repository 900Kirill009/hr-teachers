"""Вкладка «Прогноз». Пока модели нет (этап 3) — графики показывают заглушки."""
from dash import html

import charts as ch
import components as cm
import metrics as mt
from tabs import Selection


def render(sel: Selection):
    risk = mt.risk_kpis(sel.unit)
    head = [] if risk else [cm.note(
        'Прогнозная модель подключается на этапе 3: дашборд прочитает готовые вероятности '
        '(prob_stay / prob_move / prob_leave) и SHAP. Пока графики показывают заглушки.')]
    district = sel.district
    if sel.school is not None and not sel.unit.empty:
        district = sel.unit['district'].iloc[0]
    groups = ch.agg_risk_groups(sel.df, sel.year, sel.school)
    return head + [
        cm.kpi_row([
            cm.kpi('Вероятно останутся', cm.fmt(risk.get('prob_stay'), 1, '%')),
            cm.kpi('Вероятно перейдут', cm.fmt(risk.get('prob_move'), 1, '%'), accent='blue'),
            cm.kpi('Вероятно уйдут', cm.fmt(risk.get('prob_leave'), 1, '%'), accent='orange'),
            cm.kpi('Высокий риск', cm.fmt(risk.get('risk_high_n'), 0),
                   f'{cm.fmt(risk.get("risk_high"), 1, "%")} педагогов' if risk else None,
                   accent='orange'),
        ]),
        html.Div([
            html.Div(cm.graph(ch.fig_risk_by_school(sel.df, sel.year, district)), className='span-6'),
            html.Div(cm.graph(ch.fig_forecast_by_subject(sel.df, sel.year, sel.school)),
                     className='span-6'),
        ], className='grid'),
        html.Div([
            html.Div(cm.graph(ch.fig_shap_importance(None)), className='span-5'),
            html.Div(cm.graph(ch.fig_risk_groups_table(groups)), className='span-7'),
        ], className='grid'),
    ]
