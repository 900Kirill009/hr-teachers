# import pandas as pd
# from charts import get_age_structure_fig # импортируем вашу функцию

# # 1. Загружаем данные напрямую (минуя data.py, если он тоже не готов)
# df = pd.read_parquet("data/teachers_clean.parquet") 

# # 2. Берем тестовые параметры (например, самая частая школа за последний год)
# test_year = df['year'].max()
# test_school = df[df['year'] == test_year]['school_num'].value_counts().index[0]

# print(f"🔍 Тестируем: Школа №{test_school}, {test_year} год")

# # 3. Вызываем функцию построения графика
# fig = get_age_structure_fig(df, school_num=test_school, year=test_year)

# # 4. Открываем график в браузере одним кликом
# fig.show()

import pandas as pd
import charts as ch

print("🚀 Загрузка данных...")
# Путь относительно папки dashboard/
df = pd.read_parquet('data/teachers.parquet')

# Проверяем, что данные загрузились (используем версию с 39 колонками, если она есть, 
# или 14, если нет — графики адаптируются)
print(f"Загружено строк: {len(df)}, колонок: {df.shape[1]}")

# Определяем доступные годы и школу для тестов
available_years = sorted(df['year'].unique())
test_year_mobility = max([y for y in available_years if df[df['year']==y]['target'].notna().any()] or [2023])
test_year_static = max(available_years)
test_school = int(df[df['year'] == test_year_static]['school_num'].value_counts().index[0])
test_district = df[df['school_num'] == test_school]['district'].iloc[0]

print(f"\n🔍 Тестовые параметры:")
print(f"   Год (статика): {test_year_static}")
print(f"   Год (мобильность): {test_year_mobility}")
print(f"   Школа: №{test_school} ({test_district})")

# ---------------------------------------------------------------------------
# ГРУППА 1: Статика и структура (Требование 1 + референс)
# ---------------------------------------------------------------------------
print("\n1️⃣  Возрастная структура (Москва)...")
ch.fig_age_moscow(df, test_year_static).show()

print("2️⃣  Педагоги по предметам...")
ch.fig_teachers_by_subject(df, test_year_static, school_num=test_school).show()

print("3️⃣  Где школа отстаёт от Москвы...")
# Если нет колонок pk_recent, график покажет только 3 метрики вместо 4 — это ок
ch.fig_gaps_vs_moscow(df, test_year_static, test_school).show()

print("4️⃣  Возрастная структура (Школа vs Москва)...")
ch.fig_age_school_vs_moscow(df, test_year_static, test_school).show()

print("5️⃣  Квалификационные категории...")
ch.fig_qualification_categories(df, test_year_static, test_school).show()

print("6️⃣  Образование и профразвитие...")
# Покажет заглушку, если нет колонок образования/ПК, но не упадёт
ch.fig_education_profdev(df, test_year_static, test_school).show()

# ---------------------------------------------------------------------------
# ГРУППА 2: Мобильность (Требование 2 + референс)
# ---------------------------------------------------------------------------
print("\n7️⃣  Фактическая мобильность (школы округа)...")
ch.fig_mobility_actual(df, year=test_year_mobility, district=test_district).show()

print("8️⃣  Динамика по годам...")
ch.fig_dynamics_years(df, district=test_district).show()

# ---------------------------------------------------------------------------
# ГРУППА 3: Прогнозы (должны показать аккуратные заглушки)
# ---------------------------------------------------------------------------
print("\n9️⃣  Группы риска по школам (ожидается заглушка)...")
ch.fig_risk_by_school(df, test_year_static).show()

print("🔟 Прогнозный статус по предметам (ожидается заглушка)...")
ch.fig_forecast_by_subject(df, test_year_static).show()

print("1️⃣1️ Что влияет на прогноз (ожидается заглушка)...")
ch.fig_shap_importance(None).show()

print("1️⃣2️⃣ Таблица групп риска (ожидается заглушка)...")
empty_groups = ch.agg_risk_groups(df, test_year_static)
ch.fig_risk_groups_table(empty_groups).show()

print("1️⃣3️⃣ Почему такой прогноз (ожидается заглушка)...")
ch.fig_shap_explanation(None).show()

print("\n✅ Все проверки завершены. Если браузер открыл вкладки — всё работает!")