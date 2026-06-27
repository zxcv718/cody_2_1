from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from typing import TypeVar

from .command_validation import CommandValidator
from .decorators import cli_error_boundary
from .errors import BudgetAppError
from .formatters import format_budget, format_summary, format_transaction
from .services import BudgetAppService

T = TypeVar("T")


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", default=argparse.SUPPRESS, help="저장 파일 폴더 (기본값: ./data)")

    parser = argparse.ArgumentParser(prog="python -m budget_app", description="파일 기반 콘솔 가계부")
    parser.add_argument("--data-dir", default="data", help="저장 파일 폴더 (기본값: ./data)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", parents=[common], help="대화형으로 거래 추가")
    add_parser.set_defaults(handler=handle_add)

    list_parser = subparsers.add_parser("list", parents=[common], help="최신순 거래 목록")
    list_parser.add_argument("--limit", type=int, default=20, help="조회할 거래 수 (기본값: 20)")
    list_parser.set_defaults(handler=handle_list)

    search_parser = subparsers.add_parser("search", parents=[common], help="조건으로 거래 검색")
    search_parser.add_argument("--from", dest="date_from", help="시작일 YYYY-MM-DD")
    search_parser.add_argument("--to", dest="date_to", help="종료일 YYYY-MM-DD")
    search_parser.add_argument("--category", help="카테고리")
    search_parser.add_argument("--type", dest="transaction_type", help="income 또는 expense")
    search_parser.add_argument("--q", dest="query", help="메모 키워드")
    search_parser.add_argument("--tag", help="태그")
    search_parser.set_defaults(handler=handle_search)

    summary_parser = subparsers.add_parser("summary", parents=[common], help="월별 요약")
    summary_parser.add_argument("--month", required=True, help="조회 월 YYYY-MM")
    summary_parser.add_argument("--top", type=int, default=3, help="카테고리별 지출 TOP N (기본값: 3)")
    summary_parser.set_defaults(handler=handle_summary)

    budget_parser = subparsers.add_parser("budget", parents=[common], help="예산 설정/조회")
    budget_subparsers = budget_parser.add_subparsers(dest="budget_command", required=True)
    budget_set = budget_subparsers.add_parser("set", parents=[common], help="월 예산 저장")
    budget_set.add_argument("--month", required=True, help="월 YYYY-MM")
    budget_set.add_argument("--amount", required=True, help="예산 금액")
    budget_set.set_defaults(handler=handle_budget_set)
    budget_show = budget_subparsers.add_parser("show", parents=[common], help="월 예산 조회")
    budget_show.add_argument("--month", required=True, help="월 YYYY-MM")
    budget_show.set_defaults(handler=handle_budget_show)
    budget_list = budget_subparsers.add_parser("list", parents=[common], help="전체 예산 조회")
    budget_list.set_defaults(handler=handle_budget_list)

    category_parser = subparsers.add_parser("category", parents=[common], help="카테고리 관리")
    category_subparsers = category_parser.add_subparsers(dest="category_command", required=True)
    category_add = category_subparsers.add_parser("add", parents=[common], help="카테고리 추가")
    category_add.add_argument("--name", help="카테고리명")
    category_add.set_defaults(handler=handle_category_add)
    category_list = category_subparsers.add_parser("list", parents=[common], help="카테고리 목록")
    category_list.set_defaults(handler=handle_category_list)
    category_remove = category_subparsers.add_parser("remove", parents=[common], help="카테고리 삭제")
    category_remove.add_argument("--name", help="카테고리명")
    category_remove.set_defaults(handler=handle_category_remove)

    update_parser = subparsers.add_parser("update", parents=[common], help="옵션 기반 거래 수정")
    update_parser.add_argument("--id", required=True, dest="transaction_id", help="거래 id")
    update_parser.add_argument("--date", help="날짜 YYYY-MM-DD")
    update_parser.add_argument("--type", dest="transaction_type", help="income 또는 expense")
    update_parser.add_argument("--category", help="카테고리")
    update_parser.add_argument("--amount", help="금액")
    update_parser.add_argument("--memo", help="메모")
    update_parser.add_argument("--tags", help="쉼표로 구분한 태그")
    update_parser.set_defaults(handler=handle_update)

    delete_parser = subparsers.add_parser("delete", parents=[common], help="거래 삭제")
    delete_parser.add_argument("--id", required=True, dest="transaction_id", help="거래 id")
    delete_parser.set_defaults(handler=handle_delete)

    import_parser = subparsers.add_parser("import", parents=[common], help="CSV 가져오기")
    import_parser.add_argument("--from", dest="source", required=True, help="가져올 CSV 파일")
    import_parser.set_defaults(handler=handle_import)

    export_parser = subparsers.add_parser("export", parents=[common], help="CSV 내보내기")
    export_parser.add_argument("--out", required=True, help="내보낼 CSV 파일")
    export_parser.add_argument("--month", help="조회 월 YYYY-MM")
    export_parser.add_argument("--from", dest="date_from", help="시작일 YYYY-MM-DD")
    export_parser.add_argument("--to", dest="date_to", help="종료일 YYYY-MM-DD")
    export_parser.set_defaults(handler=handle_export)

    return parser


@cli_error_boundary
def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


def service_from_args(args: argparse.Namespace) -> BudgetAppService:
    return BudgetAppService(args.data_dir)


def handle_add(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    validator = CommandValidator(service)
    date = _prompt_validated("날짜(YYYY-MM-DD): ", validator.date)
    transaction_type = _prompt_validated("타입(income/expense): ", validator.transaction_type)
    category = _prompt_validated("카테고리: ", validator.category)
    amount = _prompt_validated("금액(양수): ", validator.amount)
    memo = _prompt("메모(선택): ", required=False)
    tags = _prompt("태그(쉼표로 구분, 없으면 엔터): ", required=False)
    add_input = validator.validate_add_transaction(date, transaction_type, category, amount, memo, tags)
    transaction = service.add_transaction(
        add_input.date,
        add_input.transaction_type,
        add_input.category,
        add_input.amount,
        add_input.memo,
        add_input.tags,
    )
    print(f"[저장 완료] id={transaction.id}")
    return 0


def handle_list(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    rows = service.list_transactions(args.limit)
    if not rows:
        print("데이터 없음")
        return 0
    for transaction in rows:
        print(format_transaction(transaction))
    return 0


def handle_search(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    rows = service.search_transactions(
        date_from=args.date_from,
        date_to=args.date_to,
        category=args.category,
        transaction_type=args.transaction_type,
        query=args.query,
        tag=args.tag,
    )
    if not rows:
        print("검색 결과 없음")
        return 0
    for transaction in rows:
        print(format_transaction(transaction))
    return 0


def handle_summary(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    summary = service.summarize_month(args.month, args.top)
    print(format_summary(summary, args.top))
    return 0


def handle_budget_set(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    budget = service.set_budget(args.month, args.amount)
    print(f"[저장 완료] {budget.month} 예산 {budget.amount}원")
    return 0


def handle_budget_show(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    budget = service.get_budget(args.month)
    if budget is None:
        print("데이터 없음")
    else:
        print(format_budget(budget))
    return 0


def handle_budget_list(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    budgets = service.list_budgets()
    if not budgets:
        print("데이터 없음")
        return 0
    for budget in budgets:
        print(format_budget(budget))
    return 0


def handle_category_add(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    name = args.name or _prompt("카테고리명: ")
    created = service.add_category(name)
    if created:
        print(f"[저장 완료] category={name.strip()}")
    else:
        print(f"[안내] 이미 존재하는 카테고리입니다: {name.strip()}")
    return 0


def handle_category_list(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    for name in service.list_categories():
        print(f"- {name}")
    return 0


def handle_category_remove(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    name = args.name or _prompt("카테고리명: ")
    removed = service.remove_category(name)
    if removed:
        print(f"[삭제 완료] category={name.strip()}")
        return 0
    print(f"[실패] 없는 카테고리입니다: {name.strip()}")
    return 1


def handle_update(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    updated = service.update_transaction(
        transaction_id=args.transaction_id,
        date=args.date,
        transaction_type=args.transaction_type,
        category=args.category,
        amount=args.amount,
        memo=args.memo,
        tags=args.tags,
    )
    if updated is None:
        print(f"[실패] 없는 데이터: id={args.transaction_id}")
        return 1
    print(f"[수정 완료] id={updated.id}")
    return 0


def handle_delete(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    deleted = service.delete_transaction(args.transaction_id)
    if deleted:
        print(f"[삭제 완료] id={args.transaction_id}")
        return 0
    print(f"[실패] 없는 데이터: id={args.transaction_id}")
    return 1


def handle_import(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    imported, skipped = service.import_csv(args.source)
    print(f"[완료] imported={imported}, skipped={skipped}")
    return 0


def handle_export(args: argparse.Namespace) -> int:
    service = service_from_args(args)
    count = service.export_csv(args.out, month=args.month, date_from=args.date_from, date_to=args.date_to)
    print(f"[완료] {args.out} ({count} records)")
    return 0


def _prompt(label: str, required: bool = True) -> str:
    while True:
        value = input(label).strip()
        if value or not required:
            return value
        print("[오류] 필수 입력값입니다.")


def _prompt_validated(label: str, validator: Callable[[str], T]) -> T:
    while True:
        value = _prompt(label)
        try:
            return validator(value)
        except BudgetAppError as exc:
            print(f"[오류] {exc.message}")
            if exc.hint:
                print(f"[힌트] {exc.hint}")
