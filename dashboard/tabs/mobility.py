"""Вкладка «Мобильность»: фактические переходы и уходы."""
from dash import html

import charts as ch
import components as cm
import metrics as mt
from tabs import Selection


def render(sel: Selection):
    my = mt.mobility_year(sel.df, sel.year)
    s = Selection(sel.df, my, sel.district, sel.school, sel.role)
    unit, city = mt.mobility_kpis(s.unit), mt.mobility_kpis(s.city)
    if not unit:
        return [cm.note('Нет педагогов с известным исходом для выбранных фильтров')]

    district = sel.district
    if sel.school is not None and not s.unit.empty:
        district = s.unit['district'].iloc[0]
    above, total = mt.schools_above_city(sel.df, my, district)
    prev = mt.schools_above_city(sel.df, my - 1, district) if my - 1 in set(sel.df['year']) else None

    head = []
    if my != sel.year:
        head.append(cm.note(f'Исходы {sel.year} года станут известны после выгрузки '
                            f'{sel.year + 1} года — показан {my} год.'))
    moscow = s.unit_name != 'Москва'
    head.append(cm.kpi_row([
        cm.kpi('Перешли в другую школу', cm.fmt(unit['moved'], 1, '%'),
               f'Москва — {cm.fmt(city["moved"], 1, "%")}' if moscow else f'{unit["moved_n"]} педагогов',
               accent='orange'),
        cm.kpi('Ушли из системы', cm.fmt(unit['left'], 1, '%'),
               f'Москва — {cm.fmt(city["left"], 1, "%")}' if moscow else f'{unit["left_n"]} педагогов',
               accent='orange'),
        cm.kpi('Остались', cm.fmt(unit['stayed'], 1, '%'),
               f'Москва — {cm.fmt(city["stayed"], 1, "%")}' if moscow else f'{s.unit_name}, {my}'),
        cm.kpi('Школ с оттоком выше Москвы', f'{above} из {total}',
               f'в {my - 1} — {prev[0]}' if prev and prev[1] else (district or 'по всей Москве')),
    ]))
    return head + [
        html.Div([
            html.Div(cm.graph(ch.fig_dynamics_years(sel.df, sel.district, sel.school), 400),
                     className='span-5'),
            html.Div(cm.graph(ch.fig_schools_outflow(sel.df, my, district), 400),
                     className='span-7'),
        ], className='grid'),
        cm.graph(ch.fig_mobility_heatmap(sel.df, my, sel.school, sel.district), 380),
    ]
