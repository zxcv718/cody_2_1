from __future__ import annotations

from collections.abc import Iterable, Iterator
import json
import os
from pathlib import Path
import re

from .errors import BudgetAppError
from .models import Budget, Category, Transaction

DEFAULT_CATEGORIES = ("food", "transport", "rent", "salary", "etc")
ID_PATTERN = re.compile(r"^TX-(\d+)$")


class AppPaths:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.transactions = self.data_dir / "transactions.jsonl"
        self.categories = self.data_dir / "categories.jsonl"
        self.budgets = self.data_dir / "budgets.jsonl"

    def initialize(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for path in (self.transactions, self.categories, self.budgets):
            path.touch(exist_ok=True)


def _read_json_line(line: str, path: Path) -> dict:
    try:
        value = json.loads(line)
    except json.JSONDecodeError as exc:
        raise BudgetAppError(
            f"저장 파일을 읽을 수 없습니다: {path.name}",
            "JSONL은 한 줄에 JSON 객체 하나씩 저장되어야 합니다.",
        ) from exc
    if not isinstance(value, dict):
        raise BudgetAppError(f"저장 파일 형식이 올바르지 않습니다: {path.name}", "각 줄은 JSON 객체여야 합니다.")
    return value


def _write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    tmp_path = path.with_name(f"{path.name}.tmp")
    try:
        with tmp_path.open("w", encoding="utf-8", newline="\n") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False))
                file.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


class TransactionRepository:
    def __init__(self, paths: AppPaths) -> None:
        self.path = paths.transactions

    def iter_transactions(self) -> Iterator[Transaction]:
        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if stripped:
                    yield Transaction.from_dict(_read_json_line(stripped, self.path))

    def append(self, transaction: Transaction) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as file:
            file.write(json.dumps(transaction.to_dict(), ensure_ascii=False))
            file.write("\n")

    def next_id(self) -> str:
        max_number = 0
        for transaction in self.iter_transactions():
            match = ID_PATTERN.match(transaction.id)
            if match:
                max_number = max(max_number, int(match.group(1)))
        return f"TX-{max_number + 1:06d}"

    def find_by_id(self, transaction_id: str) -> Transaction | None:
        for transaction in self.iter_transactions():
            if transaction.id == transaction_id:
                return transaction
        return None

    def replace(self, replacement: Transaction) -> bool:
        found = False

        def rows() -> Iterator[dict]:
            nonlocal found
            for transaction in self.iter_transactions():
                if transaction.id == replacement.id:
                    found = True
                    yield replacement.to_dict()
                else:
                    yield transaction.to_dict()

        _write_jsonl(self.path, rows())
        return found

    def delete(self, transaction_id: str) -> bool:
        found = False

        def rows() -> Iterator[dict]:
            nonlocal found
            for transaction in self.iter_transactions():
                if transaction.id == transaction_id:
                    found = True
                    continue
                yield transaction.to_dict()

        _write_jsonl(self.path, rows())
        return found

    def category_in_use(self, category: str) -> bool:
        return any(transaction.category == category for transaction in self.iter_transactions())


class CategoryStore:
    def __init__(self, paths: AppPaths) -> None:
        self.path = paths.categories
        self.ensure_defaults()

    def ensure_defaults(self) -> None:
        if self.path.stat().st_size == 0:
            _write_jsonl(self.path, (Category(name).to_dict() for name in DEFAULT_CATEGORIES))

    def iter_categories(self) -> Iterator[Category]:
        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if stripped:
                    yield Category.from_dict(_read_json_line(stripped, self.path))

    def list_names(self) -> list[str]:
        return [category.name for category in self.iter_categories()]

    def exists(self, name: str) -> bool:
        return name in set(self.list_names())

    def add(self, name: str) -> bool:
        names = self.list_names()
        if name in names:
            return False
        names.append(name)
        _write_jsonl(self.path, (Category(category).to_dict() for category in sorted(names)))
        return True

    def remove(self, name: str) -> bool:
        names = self.list_names()
        if name not in names:
            return False
        _write_jsonl(self.path, (Category(category).to_dict() for category in names if category != name))
        return True


class BudgetStore:
    def __init__(self, paths: AppPaths) -> None:
        self.path = paths.budgets

    def iter_budgets(self) -> Iterator[Budget]:
        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if stripped:
                    yield Budget.from_dict(_read_json_line(stripped, self.path))

    def get(self, month: str) -> Budget | None:
        for budget in self.iter_budgets():
            if budget.month == month:
                return budget
        return None

    def set(self, budget: Budget) -> None:
        budgets = {item.month: item for item in self.iter_budgets()}
        budgets[budget.month] = budget
        _write_jsonl(self.path, (budgets[month].to_dict() for month in sorted(budgets)))

    def list_all(self) -> list[Budget]:
        return sorted(self.iter_budgets(), key=lambda item: item.month)
