from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Стиль (референс: светлый карточный дашборд)
# ---------------------------------------------------------------------------
FONT       = 'Inter, "Segoe UI", system-ui, sans-serif'
CARD_BG    = '#fbfaf8'
INK        = '#1a1a1a'
MUTED      = '#767676'

BLUE_DARK  = '#17365e'   # высшая категория / тёмный акцент
BLUE_MAIN  = '#2f6db4'   # школа / первая категория / переходы
BLUE_LIGHT = '#8fb3d9'   # вторая категория / обзор по Москве
BLUE_PALE  = '#dfe8f2'   # без категории / фон Москвы
ORANGE     = '#c2571b'   # отклонения, отток, высокий риск
ORANGE_LT  = '#e8b48d'   # средний риск

AGE_ORDER  = ['до 25', '25–34', '35–44', '45–54', '55–64', '65+']

CAT_ORDER  = ['высшая', 'первая', 'вторая', 'не_найдено']
CAT_LABELS = {'высшая': 'Высшая', 'первая': 'Первая',
              'вторая': 'Вторая', 'не_найдено': 'Без категории'}
CAT_COLORS = [BLUE_DARK, BLUE_MAIN, BLUE_LIGHT, BLUE_PALE]

MOVE_ORDER  = ['перешёл в другую школу', 'ушёл из системы']
MOVE_LABELS = {'перешёл в другую школу': 'Перешли в другую школу',
               'ушёл из системы': 'Ушли из системы'}
MOVE_COLORS = [BLUE_MAIN, ORANGE]

RISK_ORDER  = ['Высокий', 'Средний', 'Низкий']
RISK_COLORS = [ORANGE, ORANGE_LT, BLUE_PALE]
RISK_HIGH, RISK_MID = 0.50, 0.25   # пороги по max(prob_leave, prob_move)

TABLE_COLS = ['Группа', 'Педагогов', 'P(перейдут)', 'P(уйдут)', 'Ключевой фактор']


# ---------------------------------------------------------------------------
# Служебные хелперы
# ---------------------------------------------------------------------------
def _school_label(s) -> str:
    return f'Школа № {s}'


def _empty_fig(title: str, msg: str = 'Нет данных для выбранных фильтров') -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, xref='paper', yref='paper',
                       x=0.5, y=0.5, font=dict(size=14, color=MUTED))
    return _style(fig, title)

def _style(fig: go.Figure, title: str, subtitle: str | None = None,
           legend: bool = False, horizontal: bool = False) -> go.Figure:
    """Приводит фигуру к единому карточному виду."""
    top = 96 if (legend and subtitle) else 80 if (legend or subtitle) else 56
    
    fig.update_layout(
        template='plotly_white', paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        font=dict(family=FONT, color=INK, size=12),
        title=dict(text=(f'<b>{title}</b>' +
                         (f'<br><span style="font-size:12px;color:{MUTED}">{subtitle}</span>'
                          if subtitle else '')),
                   x=0, xanchor='left', font=dict(family=FONT, size=15, color=INK)),
        margin=dict(l=6, r=28, t=top, b=6),
        bargap=0.35, bargroupgap=0.12,
        showlegend=legend,
        legend=dict(orientation='h', x=0, y=0.995, yanchor='top',
                    bgcolor='rgba(0,0,0,0)', font=dict(size=11)),
    )
    
    # ИСПРАВЛЕНИЕ: используем showline=False вместо line=dict(width=0)
    # Это стандартный способ скрыть оси, который работает во всех версиях Plotly.
    if horizontal:
        fig.update_yaxes(autorange='reversed', showgrid=False, zeroline=False,
                         showline=False, ticks='', automargin=True)
        fig.update_xaxes(visible=False, showgrid=False, zeroline=False)
    else:
        fig.update_xaxes(showgrid=False, zeroline=False, showline=False, 
                         ticks='', automargin=True)
        fig.update_yaxes(visible=False, showgrid=False, zeroline=False)
        
    return fig


def with_movement(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет movement_type, если его нет в данных (обычно его кладёт build_teachers.py).

    Исход года Y определяется по году Y+1: остался / перешёл в другую школу / ушёл из системы;
    для последнего года — неизвестен (NaN).
    """
    if 'movement_type' in df.columns:
        return df

    nxt = df[['id', 'year', 'school_num']].assign(year=df['year'] - 1)
    next_school = (df[['id', 'year']]
                   .merge(nxt.rename(columns={'school_num': 'next_school'}),
                          on=['id', 'year'], how='left')['next_school']
                   .set_axis(df.index))
    d = df.copy()
    d['movement_type'] = np.select(
        [d['year'] == d['year'].max(), next_school.isna(), next_school != d['school_num']],
        [None, MOVE_ORDER[1], MOVE_ORDER[0]], default='остался')
    d.loc[d['year'] == d['year'].max(), 'movement_type'] = np.nan
    return d

def add_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет risk_level из вероятностей прогноза (если они есть)."""
    if 'risk_level' in df.columns or not {'prob_leave', 'prob_move'} <= set(df.columns):
        return df
    p = df[['prob_leave', 'prob_move']].max(axis=1)
    d = df.copy()
    d['risk_level'] = np.select([p >= RISK_HIGH, p >= RISK_MID],
                                ['Высокий', 'Средний'], default='Низкий')
    return d


# ---------------------------------------------------------------------------
# 1 и 9. Мобильность / школы округа с наибольшим оттоком (horizontal stacked)
# ---------------------------------------------------------------------------
def _outflow_stack(df: pd.DataFrame, year: int, mask, top_n: int,
                   title: str, subtitle: str) -> go.Figure:
    d = with_movement(df)
    d = d[mask.loc[d.index]]
    part = d[d['year'] == year]
    if part.empty or part['movement_type'].notna().sum() == 0:
        return _empty_fig(title, f'Исходы за {year} год ещё неизвестны')
    tot = part.groupby('school_num')['id'].nunique()
    mov = (part[part['movement_type'].notna()]
           .groupby(['school_num', 'movement_type'])['id'].nunique()
           .unstack(fill_value=0).reindex(columns=MOVE_ORDER, fill_value=0))
    share = (mov.div(tot, axis=0) * 100)
    order = share.sum(axis=1).sort_values(ascending=False).head(top_n).index
    share = share.loc[order]

    fig = go.Figure()
    for m, col in zip(MOVE_ORDER, MOVE_COLORS):
        fig.add_trace(go.Bar(
            name=MOVE_LABELS[m], y=[_school_label(s) for s in share.index],
            x=share[m].round(1), orientation='h',
            marker=dict(color=col, cornerradius=3),
            texttemplate='%{value:.0f}%', textposition='auto',
            insidetextfont=dict(color='white'), outsidetextfont=dict(color=INK),
            hovertemplate='%{y}<br>' + MOVE_LABELS[m] + ': %{value:.1f}%<extra></extra>'))
    fig.update_layout(barmode='stack')
    return _style(fig, title, subtitle, legend=True, horizontal=True)


def fig_mobility_actual(df, year: int = 2024, district: str | None = None,
                        top_n: int = 10) -> go.Figure:
    mask = (df['district'] == district) if district else pd.Series(True, index=df.index)
    return _outflow_stack(df, year, mask, top_n,
                          f'Фактическая мобильность за {year}',
                          'Доля педагогов, перешедших или ушедших из системы')


def fig_schools_outflow(df, year: int, district: str, top_n: int = 10) -> go.Figure:
    return _outflow_stack(df, year, df['district'] == district, top_n,
                          'Школы округа с наибольшим оттоком',
                          f'{district} · доля ушедших/перешедших, %')


# ---------------------------------------------------------------------------
# 2. Возрастная структура — обзор по Москве (vertical bar)
# ---------------------------------------------------------------------------
def fig_age_moscow(df, year: int) -> go.Figure:
    part = df[df['year'] == year]
    if part.empty:
        return _empty_fig('Возрастная структура')
    vc = part['age_group'].value_counts(normalize=True).reindex(AGE_ORDER, fill_value=0) * 100
    fig = go.Figure(go.Bar(x=AGE_ORDER, y=vc.round(1), marker=dict(color=BLUE_LIGHT, cornerradius=3),
                           hovertemplate='%{x}: %{value:.1f}%<extra>Москва</extra>'))
    return _style(fig, 'Возрастная структура', 'Обзор по Москве · доля педагогов, %')


# ---------------------------------------------------------------------------
# 3. Педагоги по предметам (horizontal bar)
# ---------------------------------------------------------------------------
def fig_teachers_by_subject(df, year: int, school_num: int | None = None,
                            top_n: int = 15) -> go.Figure:
    part = df[(df['year'] == year) & (df['speciality'] != 'не указано')]
    if school_num is not None:
        part = part[part['school_num'] == school_num]
    if part.empty:
        return _empty_fig('Педагоги по предметам')
    cnt = part.groupby('speciality')['id'].nunique().sort_values(ascending=False).head(top_n)
    fig = go.Figure(go.Bar(y=cnt.index, x=cnt.values, orientation='h',
                           marker=dict(color=BLUE_MAIN, cornerradius=3),
                           text=cnt.values, textposition='outside',
                           outsidetextfont=dict(color=INK),
                           hovertemplate='%{y}: %{x} педагогов<extra></extra>'))
    return _style(fig, 'Педагоги по предметам', 'Число уникальных педагогов', horizontal=True)


# ---------------------------------------------------------------------------
# 4. Где школа отстаёт от Москвы (horizontal bar, отклонения в п.п.)
# ---------------------------------------------------------------------------
def _gap_metrics(sch: pd.DataFrame, city: pd.DataFrame):
    out = []
    if 'pk_recent' in sch.columns:
        out.append(('ПК за последние 3 года', sch['pk_recent'].mean() * 100,
                    city['pk_recent'].mean() * 100))
    out += [
        ('Высшая категория', (sch['category_qual_cat'] == 'высшая').mean() * 100,
         (city['category_qual_cat'] == 'высшая').mean() * 100),
        ('Доля педагогов 55+', (sch['age'] >= 55).mean() * 100,
         (city['age'] >= 55).mean() * 100),
        ('Учёная степень', (sch['academic_degree_cat'] != 'не_найдено').mean() * 100,
         (city['academic_degree_cat'] != 'не_найдено').mean() * 100),
    ]
    return out


def fig_gaps_vs_moscow(df, year: int, school_num: int) -> go.Figure:
    city = df[df['year'] == year]
    sch = city[city['school_num'] == school_num]
    if sch.empty:
        return _empty_fig('Где школа отстаёт от Москвы')
    rows = [(n, s - c) for n, s, c in _gap_metrics(sch, city)]
    rows.sort(key=lambda r: abs(r[1]), reverse=True)
    labels = [r[0] for r in rows]
    devs = [r[1] for r in rows]
    texts = [f'{v:+.1f} п.п.'.replace('-', '−') for v in devs]
    fig = go.Figure(go.Bar(y=labels, x=[round(v, 1) for v in devs], orientation='h',
                           marker=dict(color=ORANGE, cornerradius=3),
                           text=texts, textposition='outside', cliponaxis=False,
                           outsidetextfont=dict(color=INK),
                           hovertemplate='%{y}: %{text}<extra></extra>'))
    fig.add_vline(x=0, line_width=1, line_color=MUTED)
    return _style(fig, 'Где школа отстаёт от Москвы',
                  'Отклонение от среднего по городу, п.п.', horizontal=True)


# ---------------------------------------------------------------------------
# 5. Возрастная структура — школа vs Москва (grouped vertical bar)
# ---------------------------------------------------------------------------
def fig_age_school_vs_moscow(df, year: int, school_num: int) -> go.Figure:
    city = df[df['year'] == year]
    sch = city[city['school_num'] == school_num]
    if sch.empty:
        return _empty_fig('Возрастная структура')
    fig = go.Figure()
    for name, sub, col in (('Школа', sch, BLUE_MAIN), ('Москва', city, BLUE_PALE)):
        vc = sub['age_group'].value_counts(normalize=True).reindex(AGE_ORDER, fill_value=0) * 100
        fig.add_trace(go.Bar(name=name, x=AGE_ORDER, y=vc.round(1),
                             marker=dict(color=col, cornerradius=3),
                             hovertemplate=name + ' · %{x}: %{value:.1f}%<extra></extra>'))
    fig.update_layout(barmode='group')
    return _style(fig, 'Возрастная структура', 'Доля педагогов, % · школа и Москва',
                  legend=True)


# ---------------------------------------------------------------------------
# 6. Квалификационные категории (horizontal 100% stacked)
# ---------------------------------------------------------------------------
def fig_qualification_categories(df, year: int, school_num: int) -> go.Figure:
    city = df[df['year'] == year]
    sch = city[city['school_num'] == school_num]
    if sch.empty:
        return _empty_fig('Квалификационные категории')
    district = sch['district'].dropna().unique()
    district = district[0] if len(district) else None
    rows = [('Школа', sch),
            (district or 'Округ', city[city['district'] == district] if district else city.iloc[0:0]),
            ('Москва', city)]
    fig = go.Figure()
    for c, col in zip(CAT_ORDER, CAT_COLORS):
        vals = [(sub['category_qual_cat'] == c).mean() * 100 if len(sub) else 0
                for _, sub in rows]
        fig.add_trace(go.Bar(
            name=CAT_LABELS[c], y=[n for n, _ in rows], x=[round(v, 1) for v in vals],
            orientation='h', marker=dict(color=col, cornerradius=2),
            text=[f'{v:.0f}' for v in vals], textposition='inside',
            insidetextfont=dict(color=INK if col == BLUE_PALE else 'white'),
            hovertemplate='%{y} · ' + CAT_LABELS[c] + ': %{value:.1f}%<extra></extra>'))
    fig.update_layout(barmode='stack')
    return _style(fig, 'Квалификационные категории', 'Структура, % от педагогов',
                  legend=True, horizontal=True)


# ---------------------------------------------------------------------------
# 7. Образование и профразвитие (bar = школа, засечка = Москва)
# ---------------------------------------------------------------------------
EDU_METRICS = [
    ('Высшее педагогическое', 'edu_pedagogical', 'pct'),
    ('Специализация = предмет', 'edu_speciality_match', 'pct'),
    ('Прошли переподготовку (ПП)', 'retraining', 'pct'),
    ('Часы обучения за 3 года, ср.', 'pk_hours_3y', 'mean'),
]


def fig_education_profdev(df, year: int, school_num: int) -> go.Figure:
    city = df[df['year'] == year]
    sch = city[city['school_num'] == school_num]
    avail = [m for m in EDU_METRICS if m[1] in city.columns]
    if sch.empty or not avail:
        return _empty_fig('Образование и профразвитие',
                          'Нет колонок образования/ПК (см. контракт данных)')
    labels, sv, cv, texts = [], [], [], []
    for name, col, how in avail:
        f = (lambda s: s.mean() * 100) if how == 'pct' else (lambda s: s.mean())
        labels.append(name); sv.append(f(sch[col])); cv.append(f(city[col]))
        texts.append(f'{sv[-1]:.0f}  ·  Москва {cv[-1]:.0f}')
    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=[round(v, 1) for v in sv], orientation='h', name='Школа',
                         marker=dict(color=BLUE_LIGHT, cornerradius=3),
                         text=texts, textposition='outside', cliponaxis=False,
                         outsidetextfont=dict(color=INK),
                         hovertemplate='%{y}: %{text}<extra></extra>'))
    fig.add_trace(go.Scatter(y=labels, x=[round(v, 1) for v in cv], mode='markers',
                             name='Москва',
                             marker=dict(symbol='line-ns', size=18, color=INK,
                                         line=dict(width=2.5, color=INK)),
                             hovertemplate='%{y}: %{x:.0f}<extra>Москва</extra>'))
    return _style(fig, 'Образование и профразвитие',
                  'Школа (полоса) и Москва (засечка)', horizontal=True)


# ---------------------------------------------------------------------------
# 8. Динамика по годам (vertical stacked)
# ---------------------------------------------------------------------------
def fig_dynamics_years(df, district: str | None = None,
                       school_num: int | None = None) -> go.Figure:
    d = with_movement(df)
    if district:
        d = d[d['district'] == district]
    if school_num is not None:
        d = d[d['school_num'] == school_num]
    known = d[d['movement_type'].notna()]
    if known.empty:
        return _empty_fig('Динамика по годам')
    years = sorted(known['year'].unique())
    denom = d[d['year'].isin(years)].groupby('year')['id'].nunique()
    seg = (known.groupby(['year', 'movement_type'])['id'].nunique()
           .unstack(fill_value=0).reindex(columns=MOVE_ORDER, fill_value=0))
    share = seg.div(denom, axis=0) * 100
    fig = go.Figure()
    for m, col in zip(MOVE_ORDER, MOVE_COLORS):
        fig.add_trace(go.Bar(name=MOVE_LABELS[m], x=[str(y) for y in share.index],
                             y=share[m].round(1), marker=dict(color=col, cornerradius=3),
                             texttemplate='%{value:.0f}%', textposition='auto',
                             insidetextfont=dict(color='white'),
                             outsidetextfont=dict(color=INK),
                             hovertemplate='%{x} · ' + MOVE_LABELS[m] +
                                           ': %{value:.1f}%<extra></extra>'))
    fig.update_layout(barmode='stack')
    return _style(fig, 'Динамика по годам', 'Доля педагогов, %', legend=True)


# ---------------------------------------------------------------------------
# 10. Группы риска по школам (horizontal stacked)
# ---------------------------------------------------------------------------
def fig_risk_by_school(df, year: int, district: str | None = None,
                       top_n: int = 10) -> go.Figure:
    d = add_risk(df[df['year'] == year])
    if 'risk_level' not in d.columns:
        return _empty_fig('Группы риска по школам', 'Нет прогноза (prob_leave/prob_move)')
    if district:
        d = d[d['district'] == district]
    tot = d.groupby('school_num')['id'].nunique()
    seg = (d.groupby(['school_num', 'risk_level'])['id'].nunique()
           .unstack(fill_value=0).reindex(columns=RISK_ORDER, fill_value=0))
    share = seg.div(tot, axis=0) * 100
    order = share['Высокий'].sort_values(ascending=False).head(top_n).index
    share = share.loc[order]
    fig = go.Figure()
    for r, col in zip(RISK_ORDER, RISK_COLORS):
        fig.add_trace(go.Bar(name=r, y=[_school_label(s) for s in share.index],
                             x=share[r].round(1), orientation='h',
                             marker=dict(color=col, cornerradius=3),
                             texttemplate='%{value:.0f}%', textposition='auto',
                             insidetextfont=dict(color='white' if r == 'Высокий' else INK),
                             outsidetextfont=dict(color=INK),
                             hovertemplate='%{y} · ' + r + ': %{value:.1f}%<extra></extra>'))
    fig.update_layout(barmode='stack')
    return _style(fig, 'Группы риска по школам', 'Доля педагогов по уровню риска',
                  legend=True, horizontal=True)


# ---------------------------------------------------------------------------
# 11. Прогнозный статус по предметам (horizontal stacked)
# ---------------------------------------------------------------------------
def fig_forecast_by_subject(df, year: int, school_num: int | None = None,
                            top_n: int = 12) -> go.Figure:
    d = df[(df['year'] == year) & (df['speciality'] != 'не указано')]
    if school_num is not None:
        d = d[d['school_num'] == school_num]
    if d.empty or not {'prob_move', 'prob_leave'} <= set(d.columns):
        return _empty_fig('Прогнозный статус по предметам', 'Нет прогноза (prob_leave/prob_move)')
    g = d.groupby('speciality')[['prob_move', 'prob_leave']].mean() * 100
    g = g.assign(total=g.sum(axis=1)).sort_values('total', ascending=False).head(top_n)
    fig = go.Figure()
    for col, name, color in (('prob_move', 'Перейдут в другую школу', BLUE_MAIN),
                             ('prob_leave', 'Уйдут из системы', ORANGE)):
        fig.add_trace(go.Bar(name=name, y=g.index, x=g[col].round(1), orientation='h',
                             marker=dict(color=color, cornerradius=3),
                             texttemplate='%{value:.0f}%', textposition='auto',
                             insidetextfont=dict(color='white'),
                             outsidetextfont=dict(color=INK),
                             hovertemplate='%{y} · ' + name +
                                           ': %{value:.1f}%<extra></extra>'))
    fig.update_layout(barmode='stack')
    return _style(fig, 'Прогнозный статус по предметам', 'Ожидаемая доля педагогов, %',
                  legend=True, horizontal=True)


# ---------------------------------------------------------------------------
# 12. Что сильнее всего влияет на прогноз (|SHAP|, horizontal bar)
# ---------------------------------------------------------------------------
def fig_shap_importance(shap_df: pd.DataFrame | None, top_n: int = 12) -> go.Figure:
    if shap_df is None or shap_df.empty:
        return _empty_fig('Что сильнее всего влияет на прогноз',
                          'Нет shap_summary.csv (feature, mean_abs_shap)')
    d = shap_df.sort_values('mean_abs_shap', ascending=False).head(top_n)
    fig = go.Figure(go.Bar(y=d['feature'], x=d['mean_abs_shap'].round(3), orientation='h',
                           marker=dict(color=BLUE_MAIN, cornerradius=3),
                           text=d['mean_abs_shap'].round(2), textposition='outside',
                           outsidetextfont=dict(color=INK),
                           hovertemplate='%{y}: %{x:.3f}<extra></extra>'))
    return _style(fig, 'Что сильнее всего влияет на прогноз',
                  'Средний вклад признака по модулю, |SHAP|', horizontal=True)


# ---------------------------------------------------------------------------
# 13. Группы педагогов с наибольшим риском (таблица)
# ---------------------------------------------------------------------------
def agg_risk_groups(df, year: int, school_num: int | None = None, top_n: int = 8,
                    shap_long: pd.DataFrame | None = None) -> pd.DataFrame:
    """Собирает строки таблицы риска: группа → метрики + ключевой фактор."""
    d = add_risk(df[df['year'] == year])
    if school_num is not None:
        d = d[d['school_num'] == school_num]
    if not {'prob_move', 'prob_leave'} <= set(d.columns):
        return pd.DataFrame(columns=TABLE_COLS)
    d = d[d['speciality'] != 'не указано']
    g = (d.groupby('speciality')
          .agg(n=('id', 'nunique'), move=('prob_move', 'mean'), leave=('prob_leave', 'mean')))
    g = g[g['n'] >= 5].sort_values(['leave', 'move'], ascending=False).head(top_n)
    rows = []
    for subj, r in g.iterrows():
        factor = '—'
        if shap_long is not None:
            ids = d.loc[d['speciality'] == subj, ['id', 'year']]
            key = shap_long.merge(ids, on=['id', 'year'])
            if len(key):
                factor = (key.assign(a=key['contribution'].abs())
                          .groupby('feature')['a'].mean().idxmax())
        rows.append([subj, int(r['n']), f'{r["move"] * 100:.0f}%',
                     f'{r["leave"] * 100:.0f}%', factor])
    return pd.DataFrame(rows, columns=TABLE_COLS)


def fig_risk_groups_table(groups_df: pd.DataFrame) -> go.Figure:
    if groups_df is None or groups_df.empty:
        return _empty_fig('Группы педагогов с наибольшим риском', 'Нет прогноза')
    n = len(groups_df)
    fig = go.Figure(go.Table(
        header=dict(values=list(groups_df.columns), fill=dict(color=BLUE_DARK),
                    font=dict(color='white', family=FONT, size=12),
                    align=['left', 'right', 'right', 'right', 'left'], height=30),
        cells=dict(values=[groups_df[c].tolist() for c in groups_df.columns],
                   align=['left', 'right', 'right', 'right', 'left'],
                   fill=dict(color=['#ffffff' if i % 2 else CARD_BG for i in range(n)]),
                   font=dict(family=FONT, size=12, color=INK), height=28)))
    fig.update_layout(margin=dict(l=6, r=6, t=56, b=6))
    return _style(fig, 'Группы педагогов с наибольшим риском',
                  'Группы по предметам · метрики риска')


# ---------------------------------------------------------------------------
# 14. Почему такой прогноз (двусторонняя диаграмма отклонений)
# ---------------------------------------------------------------------------
def fig_shap_explanation(contrib_df: pd.DataFrame | None) -> go.Figure:
    if contrib_df is None or contrib_df.empty:
        return _empty_fig('Почему такой прогноз',
                          'Нет shap_explanation.csv (factor, value, contribution)')
    d = contrib_df.sort_values('contribution')
    colors = [ORANGE if c > 0 else BLUE_MAIN for c in d['contribution']]
    fig = go.Figure(go.Bar(
        y=[f'{f} = {v}' for f, v in zip(d['factor'], d['value'])],
        x=d['contribution'].round(3), orientation='h',
        marker=dict(color=colors, cornerradius=3),
        text=[f'{c:+.2f}' for c in d['contribution']], textposition='outside',
        cliponaxis=False, outsidetextfont=dict(color=INK),
        hovertemplate='%{y}: %{x:+.3f}<extra></extra>'))
    fig.add_vline(x=0, line_width=1, line_color=INK)
    return _style(fig, 'Почему такой прогноз',
                  'Вклад в риск: влево — снижает, вправо — повышает', horizontal=True)