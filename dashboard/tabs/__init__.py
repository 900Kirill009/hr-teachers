from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Selection:
    """Текущий выбор пользователя: данные после доп. фильтров (все годы, весь город) + срез."""
    df: pd.DataFrame
    year: int
    district: str | None
    school: int | None
    role: str

    @property
    def unit(self) -> pd.DataFrame:
        """Выбранная школа / округ / весь город за год."""
        d = self.df[self.df['year'] == self.year]
        if self.school is not None:
            return d[d['school_num'] == self.school]
        if self.district:
            return d[d['district'] == self.district]
        return d

    @property
    def city(self) -> pd.DataFrame:
        return self.df[self.df['year'] == self.year]

    @property
    def unit_name(self) -> str:
        if self.school is not None:
            return f'Школа № {self.school}'
        return self.district or 'Москва'
