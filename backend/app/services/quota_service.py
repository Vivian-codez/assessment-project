"""Monthly Usage & Quota Management Service.

Tracks tenant evaluation quotas and token metrics per calendar billing month.
Handles quota exhaustion gracefully without raising unhandled exceptions or 500 errors.
"""

import uuid
from datetime import datetime, timezone
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.logging import logger
from app.models.assignment_folder import MonthlyUsage


DEFAULT_MONTHLY_QUOTA = getattr(settings, "DEFAULT_MONTHLY_SUBMISSION_QUOTA", 100)


def get_current_billing_month() -> str:
    """Returns the current UTC billing month in YYYY-MM format, e.g. '2026-11'."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def get_or_create_monthly_usage(
    db: Session,
    user_id: str,
    billing_month: Optional[str] = None,
) -> MonthlyUsage:
    """Retrieves or safely creates a MonthlyUsage record for the given user and billing month."""
    month = billing_month or get_current_billing_month()

    # Query for existing row
    usage = (
        db.query(MonthlyUsage)
        .filter(
            MonthlyUsage.user_id == str(user_id),
            MonthlyUsage.billing_month == month,
        )
        .first()
    )
    if usage:
        return usage

    # Initialize new record if none exists
    usage = MonthlyUsage(
        id=str(uuid.uuid4()),
        user_id=str(user_id),
        billing_month=month,
        submissions_evaluated=0,
        token_count=0,
    )
    try:
        db.add(usage)
        db.commit()
        db.refresh(usage)
        logger.info(f"[QUOTA] Initialized MonthlyUsage record for user={user_id} month={month}")
        return usage
    except IntegrityError:
        # Race condition handling: Another thread/request created the record simultaneously
        db.rollback()
        usage = (
            db.query(MonthlyUsage)
            .filter(
                MonthlyUsage.user_id == str(user_id),
                MonthlyUsage.billing_month == month,
            )
            .first()
        )
        return usage


def check_and_increment_monthly_quota(
    db: Session,
    user_id: str,
    count: int = 1,
    max_quota: Optional[int] = None,
) -> Tuple[bool, MonthlyUsage, int]:
    """Calculates usage for the current calendar month and atomically reserves quota.

    Args:
        db: Active SQLAlchemy database session.
        user_id: UUID string of the authenticated tenant user.
        count: Number of submissions requesting evaluation.
        max_quota: Configurable upper limit (defaults to DEFAULT_MONTHLY_QUOTA, e.g. 100).

    Returns:
        A tuple of (allowed: bool, usage: MonthlyUsage, remaining_quota: int).
        - If allowed is True: quota has been reserved and submissions_evaluated incremented.
        - If allowed is False: quota was exhausted; usage was NOT incremented.
    """
    limit = max_quota if max_quota is not None else DEFAULT_MONTHLY_QUOTA
    month = get_current_billing_month()

    usage = get_or_create_monthly_usage(db=db, user_id=user_id, billing_month=month)

    current_evals = usage.submissions_evaluated
    remaining = max(0, limit - current_evals)

    # Check if requested count exceeds available monthly quota
    if current_evals + count > limit:
        logger.warning(
            f"[QUOTA-EXHAUSTED] User {user_id} exceeded monthly quota for {month}: "
            f"current={current_evals}, requested={count}, limit={limit}"
        )
        return False, usage, remaining

    # Quota is available: increment counter and persist atomically
    usage.submissions_evaluated = current_evals + count
    usage.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(usage)

    remaining_after = max(0, limit - usage.submissions_evaluated)
    logger.info(
        f"[QUOTA-RESERVED] User {user_id} reserved {count} eval(s) for {month}: "
        f"new_total={usage.submissions_evaluated}/{limit}, remaining={remaining_after}"
    )
    return True, usage, remaining_after


def record_token_usage(
    db: Session,
    user_id: str,
    token_count: int,
    billing_month: Optional[str] = None,
) -> None:
    """Updates accumulated Gemini API token consumption for the user in the billing month."""
    if token_count <= 0:
        return

    month = billing_month or get_current_billing_month()
    try:
        usage = get_or_create_monthly_usage(db=db, user_id=user_id, billing_month=month)
        usage.token_count += int(token_count)
        usage.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"[QUOTA-TOKENS] Added {token_count} tokens to user={user_id} month={month} (total={usage.token_count})")
    except Exception as exc:
        logger.error(f"[QUOTA-TOKENS-ERR] Failed updating token count for user {user_id}: {exc}")
        db.rollback()

