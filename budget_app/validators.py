from __future__ import annotations

from datetime import datetime

from .errors import BudgetAppError

TRANSACTION_TYPES = {"income", "expense"}


def validate_date(value: str) -> str:
    value = value.strip()
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise BudgetAppError(
            "날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).",
            "예: 2024-01-15",
        ) from exc
    if parsed.strftime("%Y-%m-%d") != value:
        raise BudgetAppError("날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).", "예: 2024-01-15")
    return value


def validate_month(value: str) -> str:
    value = value.strip()
    try:
        parsed = datetime.strptime(f"{value}-01", "%Y-%m-%d")
    except ValueError as exc:
        raise BudgetAppError("월 형식이 올바르지 않습니다 (YYYY-MM).", "예: 2024-01") from exc
    if parsed.strftime("%Y-%m") != value:
        raise BudgetAppError("월 형식이 올바르지 않습니다 (YYYY-MM).", "예: 2024-01")
    return value


def validate_amount(value: str | int) -> int:
    try:
        amount = int(str(value).strip())
    except ValueError as exc:
        raise BudgetAppError("금액은 양수 정수여야 합니다.", "예: 15000") from exc
    if amount <= 0:
        raise BudgetAppError("금액은 양수 정수여야 합니다.", "0보다 큰 정수를 입력하세요.")
    return amount


def validate_transaction_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in TRANSACTION_TYPES:
        raise BudgetAppError("타입은 income 또는 expense만 사용할 수 있습니다.", "예: income 또는 expense")
    return normalized


def validate_category_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise BudgetAppError("카테고리명은 비어 있을 수 없습니다.", "예: food")
    if "\n" in normalized or "\r" in normalized:
        raise BudgetAppError("카테고리명에 줄바꿈을 포함할 수 없습니다.", "한 줄짜리 이름을 입력하세요.")
    return normalized


def parse_tags(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        parts = value
    else:
        parts = value.split(",")

    tags: list[str] = []
    seen: set[str] = set()
    for part in parts:
        tag = str(part).strip()
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags
