from sqlalchemy import func
from sqlalchemy.sql import ColumnElement


def case_insensitive_like(column: ColumnElement, value: str, *, prefix: bool = False):
    """Return a case-insensitive LIKE expression.

    If ``prefix`` is True, match only the start of the value.
    """
    pattern = f"{value.lower()}%" if prefix else f"%{value.lower()}%"
    return func.lower(column).like(pattern)
