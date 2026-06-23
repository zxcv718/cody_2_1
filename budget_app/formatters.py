from __future__ import annotations

from .models import Budget, MonthlySummary, Transaction


def format_transaction(transaction: Transaction) -> str:
    tags = f" | #{', #'.join(transaction.tags)}" if transaction.tags else ""
    return (
        f"{transaction.id} | {transaction.date} | {transaction.type:<7} | "
        f"{transaction.category} | {transaction.amount} | {transaction.memo}{tags}"
    )


def format_budget(budget: Budget) -> str:
    return f"{budget.month} | {budget.amount}원"


def format_summary(summary: MonthlySummary, top: int) -> str:
    lines: list[str] = []
    if summary.transaction_count == 0:
        lines.append("데이터 없음")
    else:
        lines.append(f"총 수입: {summary.total_income}원")
        lines.append(f"총 지출: {summary.total_expense}원")
        lines.append(f"잔액: {summary.balance}원")

    if summary.budget is not None:
        usage = 0.0 if summary.budget.amount == 0 else summary.total_expense / summary.budget.amount * 100
        lines.append(f"예산: {summary.budget.amount}원 (사용률 {usage:.1f}%)")
        if summary.total_expense > summary.budget.amount:
            lines.append("[경고] 월 예산을 초과했습니다.")

    if summary.transaction_count > 0:
        lines.append("")
        lines.append(f"지출 TOP {top}")
        for index, (category, amount) in enumerate(summary.category_expenses.most_common(top), start=1):
            lines.append(f"{index}) {category} {amount}원")
        if not summary.category_expenses:
            lines.append("지출 데이터 없음")
    return "\n".join(lines)
