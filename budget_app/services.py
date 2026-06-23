from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path
import csv
import heapq
from collections.abc import Iterator

from .errors import BudgetAppError
from .models import Budget, MonthlySummary, Transaction
from .storage import AppPaths, BudgetStore, CategoryStore, ID_PATTERN, TransactionRepository
from .validators import (
    parse_tags,
    validate_amount,
    validate_category_name,
    validate_date,
    validate_month,
    validate_transaction_type,
)

CSV_FIELDS = ("date", "type", "category", "amount", "memo", "tags")


class BudgetAppService:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.paths = AppPaths(data_dir)
        self.paths.initialize()
        self.transactions = TransactionRepository(self.paths)
        self.categories = CategoryStore(self.paths)
        self.budgets = BudgetStore(self.paths)

    def add_transaction(
        self,
        date: str,
        transaction_type: str,
        category: str,
        amount: str | int,
        memo: str = "",
        tags: str | list[str] | None = None,
    ) -> Transaction:
        category = validate_category_name(category)
        if not self.categories.exists(category):
            raise BudgetAppError(
                f"등록되지 않은 카테고리입니다: {category}",
                "`category list`로 확인하거나 `category add`로 먼저 등록하세요.",
            )

        transaction = Transaction(
            id=self.transactions.next_id(),
            type=validate_transaction_type(transaction_type),
            date=validate_date(date),
            amount=validate_amount(amount),
            category=category,
            memo=memo.strip(),
            tags=parse_tags(tags),
        )
        self.transactions.append(transaction)
        return transaction

    def list_transactions(self, limit: int = 20) -> list[Transaction]:
        if limit <= 0:
            raise BudgetAppError("조회 개수는 양수여야 합니다.", "예: --limit 10")

        heap: list[tuple[tuple[str, int], int, Transaction]] = []
        for index, transaction in enumerate(self.transactions.iter_transactions()):
            item = (_latest_key(transaction), index, transaction)
            if len(heap) < limit:
                heapq.heappush(heap, item)
            else:
                heapq.heappushpop(heap, item)
        return [item[2] for item in sorted(heap, key=lambda row: row[0], reverse=True)]

    def search_transactions(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        category: str | None = None,
        transaction_type: str | None = None,
        query: str | None = None,
        tag: str | None = None,
    ) -> list[Transaction]:
        matches = list(
            self._iter_filtered_transactions(
                date_from=date_from,
                date_to=date_to,
                category=category,
                transaction_type=transaction_type,
                query=query,
                tag=tag,
            )
        )
        return sorted(matches, key=_latest_key, reverse=True)

    def summarize_month(self, month: str, top: int = 3) -> MonthlySummary:
        month = validate_month(month)
        if top <= 0:
            raise BudgetAppError("TOP 개수는 양수여야 합니다.", "예: --top 3")

        income = 0
        expense = 0
        count = 0
        category_expenses: Counter[str] = Counter()

        for transaction in self.transactions.iter_transactions():
            if not transaction.date.startswith(month):
                continue
            count += 1
            if transaction.type == "income":
                income += transaction.amount
            else:
                expense += transaction.amount
                category_expenses[transaction.category] += transaction.amount

        return MonthlySummary(
            month=month,
            total_income=income,
            total_expense=expense,
            category_expenses=category_expenses,
            transaction_count=count,
            budget=self.budgets.get(month),
        )

    def set_budget(self, month: str, amount: str | int) -> Budget:
        budget = Budget(month=validate_month(month), amount=validate_amount(amount))
        self.budgets.set(budget)
        return budget

    def get_budget(self, month: str) -> Budget | None:
        return self.budgets.get(validate_month(month))

    def list_budgets(self) -> list[Budget]:
        return self.budgets.list_all()

    def list_categories(self) -> list[str]:
        return self.categories.list_names()

    def add_category(self, name: str) -> bool:
        return self.categories.add(validate_category_name(name))

    def remove_category(self, name: str) -> bool:
        name = validate_category_name(name)
        if self.transactions.category_in_use(name):
            raise BudgetAppError(
                f"사용 중인 카테고리는 삭제할 수 없습니다: {name}",
                "거래를 먼저 다른 카테고리로 수정한 뒤 삭제하세요.",
            )
        return self.categories.remove(name)

    def update_transaction(
        self,
        transaction_id: str,
        date: str | None = None,
        transaction_type: str | None = None,
        category: str | None = None,
        amount: str | int | None = None,
        memo: str | None = None,
        tags: str | list[str] | None = None,
    ) -> Transaction | None:
        current = self.transactions.find_by_id(transaction_id)
        if current is None:
            return None

        updates: dict[str, object] = {}
        if date is not None:
            updates["date"] = validate_date(date)
        if transaction_type is not None:
            updates["type"] = validate_transaction_type(transaction_type)
        if category is not None:
            category = validate_category_name(category)
            if not self.categories.exists(category):
                raise BudgetAppError(
                    f"등록되지 않은 카테고리입니다: {category}",
                    "`category list`로 확인하거나 `category add`로 먼저 등록하세요.",
                )
            updates["category"] = category
        if amount is not None:
            updates["amount"] = validate_amount(amount)
        if memo is not None:
            updates["memo"] = memo.strip()
        if tags is not None:
            updates["tags"] = parse_tags(tags)
        if not updates:
            raise BudgetAppError("수정할 필드가 없습니다.", "--date, --type, --category, --amount, --memo, --tags 중 하나를 입력하세요.")

        updated = replace(current, **updates)
        self.transactions.replace(updated)
        return updated

    def delete_transaction(self, transaction_id: str) -> bool:
        return self.transactions.delete(transaction_id)

    def import_csv(self, source_path: str | Path) -> tuple[int, int]:
        imported = 0
        skipped = 0
        path = Path(source_path)
        if not path.exists():
            raise BudgetAppError(f"가져올 CSV 파일이 없습니다: {path}", "파일 경로를 확인하세요.")

        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                raise BudgetAppError("CSV 헤더가 없습니다.", f"필수 헤더: {', '.join(CSV_FIELDS)}")
            missing = [field for field in CSV_FIELDS if field not in reader.fieldnames]
            if missing:
                raise BudgetAppError("CSV 필수 컬럼이 없습니다.", f"누락 컬럼: {', '.join(missing)}")

            for row in reader:
                try:
                    self.add_transaction(
                        date=row.get("date", ""),
                        transaction_type=row.get("type", ""),
                        category=row.get("category", ""),
                        amount=row.get("amount", ""),
                        memo=row.get("memo", "") or "",
                        tags=row.get("tags", "") or "",
                    )
                    imported += 1
                except BudgetAppError:
                    skipped += 1
        return imported, skipped

    def export_csv(
        self,
        output_path: str | Path,
        month: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        if month is None and date_from is None and date_to is None:
            raise BudgetAppError(
                "export는 기간 조건이 필요합니다.",
                "--month YYYY-MM 또는 --from YYYY-MM-DD --to YYYY-MM-DD를 입력하세요.",
            )
        if month is not None:
            month = validate_month(month)

        path = Path(output_path)
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for transaction in self._iter_filtered_transactions(date_from=date_from, date_to=date_to):
                if month is not None and not transaction.date.startswith(month):
                    continue
                writer.writerow(
                    {
                        "date": transaction.date,
                        "type": transaction.type,
                        "category": transaction.category,
                        "amount": transaction.amount,
                        "memo": transaction.memo,
                        "tags": ",".join(transaction.tags),
                    }
                )
                count += 1
        return count

    def _iter_filtered_transactions(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        category: str | None = None,
        transaction_type: str | None = None,
        query: str | None = None,
        tag: str | None = None,
    ) -> Iterator[Transaction]:
        if date_from:
            date_from = validate_date(date_from)
        if date_to:
            date_to = validate_date(date_to)
        if category:
            category = validate_category_name(category)
            if not self.categories.exists(category):
                raise BudgetAppError(
                    f"등록되지 않은 카테고리입니다: {category}",
                    "`category list`로 확인하거나 `category add`로 먼저 등록하세요.",
                )
        if transaction_type:
            transaction_type = validate_transaction_type(transaction_type)
        if query:
            query = query.casefold()
        if tag:
            tag = tag.strip()

        for transaction in self.transactions.iter_transactions():
            if date_from and transaction.date < date_from:
                continue
            if date_to and transaction.date > date_to:
                continue
            if category and transaction.category != category:
                continue
            if transaction_type and transaction.type != transaction_type:
                continue
            if query and query not in transaction.memo.casefold():
                continue
            if tag and tag not in transaction.tags:
                continue
            yield transaction


def _latest_key(transaction: Transaction) -> tuple[str, int]:
    match = ID_PATTERN.match(transaction.id)
    number = int(match.group(1)) if match else 0
    return transaction.date, number
