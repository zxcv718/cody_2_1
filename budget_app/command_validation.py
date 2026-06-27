from __future__ import annotations

from dataclasses import dataclass

from .errors import BudgetAppError
from .services import BudgetAppService
from .validators import (
    parse_tags,
    validate_amount,
    validate_category_name,
    validate_date,
    validate_transaction_type,
)


@dataclass(frozen=True)
class AddTransactionInput:
    date: str
    transaction_type: str
    category: str
    amount: int
    memo: str
    tags: list[str]


class CommandValidator:
    def __init__(self, service: BudgetAppService) -> None:
        self.service = service

    def date(self, value: str) -> str:
        return validate_date(value)

    def transaction_type(self, value: str) -> str:
        return validate_transaction_type(value)

    def amount(self, value: str | int) -> int:
        return validate_amount(value)

    def category(self, value: str) -> str:
        category = validate_category_name(value)
        if category not in self.service.list_categories():
            raise BudgetAppError(
                f"등록되지 않은 카테고리입니다: {category}",
                "`category list`로 확인하거나 `category add`로 먼저 등록하세요.",
            )
        return category

    def validate_add_transaction(
        self,
        date: str,
        transaction_type: str,
        category: str,
        amount: str | int,
        memo: str = "",
        tags: str | list[str] | None = None,
    ) -> AddTransactionInput:
        return AddTransactionInput(
            date=self.date(date),
            transaction_type=self.transaction_type(transaction_type),
            category=self.category(category),
            amount=self.amount(amount),
            memo=memo.strip(),
            tags=parse_tags(tags),
        )
