from __future__ import annotations

from collections.abc import Callable
from functools import wraps
import sys
from typing import ParamSpec, TypeVar

from .errors import BudgetAppError

P = ParamSpec("P")
R = TypeVar("R")


def cli_error_boundary(func: Callable[P, int]) -> Callable[P, int]:
    """Convert exceptions from command handlers into concise CLI output."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        try:
            return func(*args, **kwargs)
        except BudgetAppError as exc:
            print(f"[오류] {exc.message}", file=sys.stderr)
            if exc.hint:
                print(f"[힌트] {exc.hint}", file=sys.stderr)
            return exc.exit_code
        except (EOFError, KeyboardInterrupt):
            print("\n[오류] 입력이 취소되었습니다.", file=sys.stderr)
            print("[힌트] 명령을 다시 실행해 필요한 값을 입력하세요.", file=sys.stderr)
            return 130
        except Exception as exc:
            print("[오류] 예상하지 못한 문제가 발생했습니다.", file=sys.stderr)
            print(f"[힌트] {exc}", file=sys.stderr)
            return 1

    return wrapper
