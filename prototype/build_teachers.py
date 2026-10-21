"""Сборка data/teachers.parquet — таблицы для дашборда (1 строка = 1 педагог в 1 году).

Вход:  data/data_clean.parquet (очищенные «Педагоги», делает ноутбук дз_5),
       data/Школы.xlsx, data/Образование.xlsx, data/ПК-ПП.xlsx
Выход: data/teachers.parquet

Запуск из корня репозитория:  python prototype/build_teachers.py
Описание колонок — в README, раздел «Контракт данных».
"""
import os
import re

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

AGE_GROUPS = ['до 25', '25–34', '35–44', '45–54', '55–64', '65+']

# Статусы мобильности (по наличию педагога в данных следующего года)
STAY, MOVE, LEAVE = 0, 1, 2
MOVEMENT_LABELS = {STAY: 'остался', MOVE: 'перешёл в другую школу', LEAVE: 'ушёл из системы'}

MAX_STUDENTS_PER_TEACHER = 60

HIGHER_EDU = ('Высшее', 'Аспирантура')
PEDAGOGICAL = re.compile(r'педагог|учител|преподав', re.IGNORECASE)
SHORT_COURSE = re.compile(r'ппэ|организатор|подготовка|эксперт', re.IGNORECASE)

# Слова в «Направлении деятельности», которые не говорят о предмете
SUBJECT_STOPWORDS = {'языка', 'классов', 'культуры', 'основ', 'группы', 'дня', 'по', 'и', 'в'}
# Специализации, которые засчитываем как совпадение для целых групп предметов
SUBJECT_SYNONYMS = {
    'иностр': ['иностран', 'лингвист', 'филолог'],   # английского, немецкого, ... языка
    'русск': ['филолог'],
    'литер': ['филолог'],
    'начал': ['начальн'],
    'алгеб': ['матем'],
    'геоме': ['матем'],
    'общес': ['истор', 'социал', 'правов', 'эконом'],
    'изобр': ['художест', 'искусств', 'дизайн'],
    'техно': ['труд', 'технолог'],
    'безоп': ['безопасн'],
}
FOREIGN = ('английск', 'немецк', 'французск', 'испанск', 'китайск', 'итальянск', 'арабск')


# ---------------------------------------------------------------------------
# База: те же шаги, что в ноутбуке «Движуха в кадрах»
# ---------------------------------------------------------------------------
def build_base(df_clean: pd.DataFrame, schools: pd.DataFrame) -> pd.DataFrame:
    teachers = df_clean.drop_duplicates(['id', 'year']).copy()
    teachers['age_group'] = pd.cut(teachers['age'], bins=[0, 24, 34, 44, 54, 64, np.inf],
                                   labels=AGE_GROUPS, include_lowest=True)
    district = (schools[['Школа', 'Округ']].drop_duplicates('Школа')
                .rename(columns={'Школа': 'school_num', 'Округ': 'district'}))
    teachers = teachers.merge(district, on='school_num', how='left')
    return teachers[[
        'id', 'year', 'school_num', 'district', 'main_position_cat', 'age', 'age_group',
        'experience_age_pedagogic_clean', 'experience_age_all_clean', 'category_qual_cat',
        'category_due_clean', 'class_manager', 'speciality', 'target', 'sex',
        'academic_degree_cat',
    ]].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Мобильность: 0 — остался, 1 — перешёл в другую школу, 2 — ушёл из системы
# ---------------------------------------------------------------------------
def add_mobility(t: pd.DataFrame) -> pd.DataFrame:
    nxt = t[['id', 'year', 'school_num']].copy()
    nxt['year'] -= 1  # строка года Y+1 приклеивается к году Y
    t = t.merge(nxt.rename(columns={'school_num': 'next_school'}), on=['id', 'year'], how='left')

    known = t['year'] < t['year'].max()  # для последнего года исход ещё неизвестен
    status = np.select([t['next_school'].isna(), t['next_school'] != t['school_num']],
                       [LEAVE, MOVE], default=STAY).astype(float)
    t['mobility_status'] = pd.Series(np.where(known, status, np.nan), index=t.index).astype('Int8')
    t['movement_type'] = t['mobility_status'].map(MOVEMENT_LABELS)
    return t.drop(columns='next_school')


# ---------------------------------------------------------------------------
# Нагрузка: предметы и параллели (из построчных записей «Педагогов»)
# ---------------------------------------------------------------------------
def add_load(t: pd.DataFrame, df_clean: pd.DataFrame, schools: pd.DataFrame) -> pd.DataFrame:
    load = (df_clean.groupby(['id', 'year'])
            .agg(n_subjects=('subject', 'nunique'), n_parallels=('parallel', 'nunique'),
                 min_parallel=('parallel', 'min'), max_parallel=('parallel', 'max'))
            .reset_index())
    pairs = (df_clean[['id', 'year', 'subject', 'parallel']].drop_duplicates()
             .groupby(['id', 'year']).size().rename('n_subject_parallel').reset_index())
    t = t.merge(load, on=['id', 'year'], how='left').merge(pairs, on=['id', 'year'], how='left')

    # Учеников на педагога: контингент школы (один срез) / педагоги школы в этом году
    staff = t.groupby(['school_num', 'year'])['id'].nunique().rename('school_teachers').reset_index()
    contingent = schools[['Школа', 'Общая численность контингента']].rename(
        columns={'Школа': 'school_num', 'Общая численность контингента': 'school_students'})
    staff = staff.merge(contingent, on='school_num', how='left')
    ratio = staff['school_students'] / staff['school_teachers']
    # У части школ в данных лишь несколько педагогов (медиана 5) — штат выгружен не целиком.
    # В распределении разрыв: полные школы ≤ 60 учеников на педагога, неполные — от 100.
    staff['school_staff_complete'] = (ratio <= MAX_STUDENTS_PER_TEACHER).astype(int)
    staff['students_per_teacher'] = ratio.where(staff['school_staff_complete'] == 1)
    return t.merge(staff, on=['school_num', 'year'], how='left')


# ---------------------------------------------------------------------------
# Образование
# ---------------------------------------------------------------------------
def _subject_stems(speciality: str) -> list[str]:
    words = [w for w in str(speciality).lower().split() if w not in SUBJECT_STOPWORDS]
    stems = [w[:5] if len(w) >= 6 else w[:-1] for w in words if len(w) > 2]
    if any(w.startswith(FOREIGN) for w in words):
        stems.append('иностр')
    return stems + [s for st in stems for s in SUBJECT_SYNONYMS.get(st, [])]


def add_education(t: pd.DataFrame, edu: pd.DataFrame) -> pd.DataFrame:
    edu = edu.copy()
    edu['text'] = (edu['Наименование учебного заведения'].fillna('') + ' ' +
                   edu['Специализация'].fillna('') + ' ' + edu['Квалификация'].fillna('')).str.lower()
    edu['is_higher'] = edu['Тип образования'].str.startswith(HIGHER_EDU)
    edu['is_dpo'] = edu['Тип образования'].str.startswith('Дополнительное')
    base = edu[~edu['is_dpo']]

    g = base.groupby(['id', 'year'])
    per = pd.DataFrame({
        'edu_higher': g['is_higher'].any(),
        'edu_pedagogical': (base['is_higher'] & base['text'].str.contains(PEDAGOGICAL))
                           .groupby([base['id'], base['year']]).any(),
        'edu_text': g['text'].agg(' | '.join),
    }).reset_index()
    t = t.merge(per, on=['id', 'year'], how='left')

    # Совпадение специализации с предметом — эвристика по основам слов.
    # Считаем только для учителей: у руководителей «направление» — не предмет.
    def match(row):
        if (row['main_position_cat'] != 'учитель' or row['speciality'] == 'не указано'
                or pd.isna(row['edu_text'])):
            return np.nan
        stems = _subject_stems(row['speciality'])
        return float(any(s in row['edu_text'] for s in stems)) if stems else np.nan

    t['edu_speciality_match'] = t.apply(match, axis=1)
    t = t.drop(columns='edu_text')
    for c in ('edu_higher', 'edu_pedagogical'):
        t[c] = t[c].astype('boolean').fillna(False).astype(int)
    return t


# ---------------------------------------------------------------------------
# Повышение квалификации и переподготовка
# ---------------------------------------------------------------------------
def add_profdev(t: pd.DataFrame, edu: pd.DataFrame, pk: pd.DataFrame) -> pd.DataFrame:
    dpo = edu[edu['Тип образования'].str.startswith('Дополнительное')]
    # ДПО со специализацией/квалификацией = переподготовка (ПК их не даёт),
    # кроме курсов вроде «Организатор ППЭ», записанных в квалификацию
    short_course = dpo['Квалификация'].str.contains(SHORT_COURSE, na=False)
    is_pp = dpo['Специализация'].notna() | (dpo['Квалификация'].notna() & ~short_course)
    pp_edu = dpo[is_pp][['id', 'year']]
    pp_pk = pk[pk['type'] == 'ПП'][['id', 'year']]
    pp = pd.concat([pp_edu, pp_pk]).drop_duplicates()

    # Даты обучения: из ДПО в «Образовании» (история) и из листов ПК-ПП (текущий год)
    events = pd.concat([
        dpo[['id', 'Дата окончания']].rename(columns={'Дата окончания': 'done'}),
        pk[['id', 'year']].rename(columns={'year': 'done'}),
    ]).dropna().drop_duplicates()

    out = t[['id', 'year']].copy()
    ev = out.merge(events, on='id')
    ev = ev[(ev['done'] <= ev['year']) & (ev['done'] >= ev['year'] - 2)]
    recent = ev[['id', 'year']].drop_duplicates().assign(pk_recent=1)

    # Часы есть только в ПК-ПП (листы 2022–2024): сумма за окно [Y-2, Y]
    hours = out.merge(pk[['id', 'year', 'hours']].rename(columns={'year': 'pk_year'}), on='id')
    hours = hours[(hours['pk_year'] <= hours['year']) & (hours['pk_year'] >= hours['year'] - 2)]
    hours = hours.groupby(['id', 'year'])['hours'].sum().rename('pk_hours_3y').reset_index()
    pk_year = pk.groupby(['id', 'year']).size().rename('pk_n').reset_index()

    t = (t.merge(recent, on=['id', 'year'], how='left')
          .merge(hours, on=['id', 'year'], how='left')
          .merge(pk_year, on=['id', 'year'], how='left')
          .merge(pp.assign(retraining=1), on=['id', 'year'], how='left'))
    t['pk_recent'] = t['pk_recent'].fillna(0).astype(int)
    t['pk_hours_3y'] = t['pk_hours_3y'].fillna(0)
    t['pk_this_year'] = t['pk_n'].notna().astype(int)
    t['retraining'] = t['retraining'].fillna(0).astype(int)
    return t.drop(columns='pk_n')


def load_sheets(name: str) -> pd.DataFrame:
    sheets = pd.read_excel(os.path.join(DATA, name), sheet_name=None)
    return pd.concat([df.assign(year=int(y)) for y, df in sheets.items()], ignore_index=True)


def main():
    df_clean = pd.read_parquet(os.path.join(DATA, 'data_clean.parquet'))
    schools = pd.read_excel(os.path.join(DATA, 'Школы.xlsx'))
    print('Читаю Образование.xlsx и ПК-ПП.xlsx...')
    edu = load_sheets('Образование.xlsx')
    pk = load_sheets('ПК-ПП.xlsx')
    pk.columns = ['id', 'program', 'type', 'hours', 'date', 'year']

    t = build_base(df_clean, schools)
    t = add_mobility(t)
    t = add_load(t, df_clean, schools)
    t = add_education(t, edu)
    t = add_profdev(t, edu, pk)

    # Проверки
    assert not t.duplicated(['id', 'year']).any()
    known = t['target'].notna()
    assert ((t.loc[known, 'target'] == 1) == (t.loc[known, 'mobility_status'] == LEAVE)).all(), \
        'target=1 должен совпадать с «ушёл из системы»'

    path = os.path.join(DATA, 'teachers.parquet')
    t.to_parquet(path, index=False)
    print(f'Сохранено: {path} — {t.shape[0]:,} строк, {t.shape[1]} колонок')
    print(t.groupby('year')[['pk_recent', 'retraining', 'edu_pedagogical',
                             'edu_speciality_match', 'pk_hours_3y']].mean().round(3))
    print(pd.crosstab(t['year'], t['movement_type'].fillna('неизвестно')))


if __name__ == '__main__':
    main()
