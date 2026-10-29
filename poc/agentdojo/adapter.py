"""The bank behind the banking handles, backed by AgentDojo's own tool runtime.

Every operation a node performs goes through `FunctionsRuntime.run_function`, the
call AgentDojo's own agents make, so the benchmark's environment changes exactly
as it would under an agent and AgentDojo's unchanged scorer reads the result. The
handles in `poc/bank.py` check scope *before* calling in here, so a refused request
never reaches the tool.

Each call is recorded as an AgentDojo `FunctionCall` with its result, so the
pipeline element can emit the tool-call messages an agent would have produced
(`ground_truth_pipeline.py` does the same).

`inspect` is the scope checks' read: it reads the environment directly and is not
recorded, because it is not something a node asked for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime, TaskEnvironment
from pydantic import BaseModel

from ..bank import FILE_SCOPE_PREFIX, BankError

# A read scope → the AgentDojo tool (and arguments) that serves it.
_READS: dict[str, tuple[str, dict[str, Any]]] = {
    "transactions": ("get_most_recent_transactions", {"n": 100}),
    "scheduled-transactions": ("get_scheduled_transactions", {}),
    "balance": ("get_balance", {}),
    "iban": ("get_iban", {}),
    "user-info": ("get_user_info", {}),
}


def _plain(value: Any) -> Any:
    """A tool result as JSON-shaped data: pydantic models become dicts."""
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


@dataclass
class AgentDojoBank:
    """`poc.bank.Bank` over one AgentDojo task run's runtime and environment."""

    runtime: FunctionsRuntime
    env: TaskEnvironment
    calls: list[tuple[FunctionCall, Any, str | None]] = field(default_factory=list)

    def _call(self, function: str, args: dict[str, Any]) -> Any:
        call = FunctionCall(function=function, args=dict(args), id=f"graph-{len(self.calls)}")
        result, error = self.runtime.run_function(self.env, function, args)
        self.calls.append((call, result, error))
        if error is not None:
            raise BankError(error)
        return _plain(result)

    def read(self, scope: str) -> Any:
        if scope.startswith(FILE_SCOPE_PREFIX):
            return self._call("read_file", {"file_path": scope[len(FILE_SCOPE_PREFIX) :]})
        function, args = _READS[scope]
        return self._call(function, args)

    def inspect(self, scope: str) -> Any:
        account = self.env.bank_account  # type: ignore[attr-defined]
        if scope == "iban":
            return account.iban
        if scope == "transactions":
            return _plain(account.transactions)
        if scope == "scheduled-transactions":
            return _plain(account.scheduled_transactions)
        raise KeyError(f"no inspection of {scope!r}")

    def send_money(self, recipient: str, amount: float, subject: str, date: str) -> Any:
        args = {"recipient": recipient, "amount": amount, "subject": subject, "date": date}
        return self._call("send_money", args)

    def schedule_transaction(
        self, recipient: str, amount: float, subject: str, date: str, recurring: bool
    ) -> Any:
        args = {
            "recipient": recipient,
            "amount": amount,
            "subject": subject,
            "date": date,
            "recurring": recurring,
        }
        return self._call("schedule_transaction", args)

    def update_scheduled_transaction(self, id: int, **changes: Any) -> Any:
        return self._call("update_scheduled_transaction", {"id": id, **changes})

    def update_user_info(self, **changes: Any) -> Any:
        return self._call("update_user_info", changes)
