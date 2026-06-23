from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .errors import BudgetAppError
from .validators import parse_tags


@dataclass(frozen=True)
class Transaction:
    id: str
    type: str
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        try:
            return cls(
                id=str(data["id"]),
                type=str(data["type"]),
                date=str(data["date"]),
                amount=int(data["amount"]),
                category=str(data["category"]),
                memo=str(data.get("memo", "")),
                tags=parse_tags(data.get("tags", [])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise BudgetAppError(
                "저장된 거래 데이터가 손상되었습니다.",
                "transactions.jsonl 파일의 필수 필드(id, type, date, amount, category)를 확인하세요.",
            ) from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "date": self.date,
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": self.tags,
        }


@dataclass(frozen=True)
class Budget:
    month: str
    amount: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Budget":
        try:
            return cls(month=str(data["month"]), amount=int(data["amount"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise BudgetAppError(
                "저장된 예산 데이터가 손상되었습니다.",
                "budgets.jsonl 파일의 month, amount 필드를 확인하세요.",
            ) from exc

    def to_dict(self) -> dict[str, Any]:
        return {"month": self.month, "amount": self.amount}


@dataclass(frozen=True)
class Category:
    name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Category":
        try:
            return cls(name=str(data["name"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise BudgetAppError(
                "저장된 카테고리 데이터가 손상되었습니다.",
                "categories.jsonl 파일의 name 필드를 확인하세요.",
            ) from exc

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name}


@dataclass(frozen=True)
class MonthlySummary:
    month: str
    total_income: int
    total_expense: int
    category_expenses: Counter[str]
    transaction_count: int
    budget: Budget | None = None

    @property
    def balance(self) -> int:
        return self.total_income - self.total_expense
