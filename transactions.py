"""Validated money and immutable, session-only order provenance."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
import math
from uuid import uuid4


ORDER_STATUSES = frozenset({"CREATED", "SAVED", "APPROVED", "VOIDED", "COMPLETED", "PAYER_ACTION_REQUIRED"})


def money(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid amount.") from None
    if not result.is_finite() or result < 0 or not math.isfinite(float(result)):
        raise ValueError("Amount must be finite and nonnegative.")
    return result


def currency_code(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z]{3}", value):
        raise ValueError("A three-letter uppercase currency code is required.")
    return value


@dataclass(frozen=True)
class OrderSnapshot:
    order_id: str
    status: str
    amount: Decimal
    currency: str
    retrieved_at: str


def parse_order(payload, requested_id):
    """Only a matching, single-unit order can supply an analysis amount."""
    try:
        units = payload["purchase_units"]
        if payload["id"] != requested_id or not requested_id or len(units) != 1:
            raise ValueError
        amount = units[0]["amount"]
        if payload["status"] not in ORDER_STATUSES:
            raise ValueError
        return OrderSnapshot(
            requested_id, str(payload["status"]), money(amount["value"]),
            currency_code(amount["currency_code"]),
            datetime.now(timezone.utc).isoformat(),
        )
    except (KeyError, IndexError, TypeError, ValueError):
        raise ValueError("Order must have a matching ID and one valid currency amount.") from None


def transaction_record(amount, currency, snapshot=None):
    amount, currency = money(amount), currency_code(currency)
    linked = snapshot is not None and amount == snapshot.amount and currency == snapshot.currency
    return {
        "Transaction ID": str(uuid4()),
        "Source": "PayPal Sandbox" if linked else "Manual",
        "PayPal Order ID": snapshot.order_id if linked else "Manual",
        "PayPal Order Status": snapshot.status if linked else "N/A",
        "Order Retrieved At": snapshot.retrieved_at if linked else "N/A",
        "Analyzed At": datetime.now(timezone.utc).isoformat(),
        "Amount": str(amount), "Currency": currency,
    }


def active_order(state, *, requested_id=None, amount=None, currency=None, lookup_started=False):
    """Clear stale attribution before I/O or on edits; it cannot reattach itself."""
    snapshot = state.get("order_snapshot")
    if snapshot and (lookup_started
                     or (requested_id is not None and requested_id != snapshot.order_id)
                     or (amount is not None and money(amount) != snapshot.amount)
                     or (currency is not None and currency != snapshot.currency)):
        state.pop("order_snapshot", None)
    return state.get("order_snapshot")
