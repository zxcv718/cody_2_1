from __future__ import annotations


class BudgetAppError(Exception):
    """User-facing application error without a stack trace."""

    def __init__(self, message: str, hint: str | None = None, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.exit_code = exit_code
