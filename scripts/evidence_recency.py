from __future__ import annotations

from datetime import UTC, datetime


REFERENCE_DATE = datetime(2026, 4, 26, tzinfo=UTC)
CURRENT_WINDOW_DAYS = 180
RECENT_CONTEXT_DAYS = 730


def parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def source_age_days(published_at: str | None) -> int | None:
    published = parse_published_at(published_at)
    if published is None:
        return None
    return max(0, (REFERENCE_DATE - published).days)


def source_recency_bucket(published_at: str | None) -> str:
    age_days = source_age_days(published_at)
    if age_days is None:
        return "unknown"
    if age_days <= CURRENT_WINDOW_DAYS:
        return "current_window"
    if age_days <= RECENT_CONTEXT_DAYS:
        return "recent_context"
    return "historical_context"


def current_form_allowed(published_at: str | None) -> bool:
    return source_recency_bucket(published_at) == "current_window"


def evidence_roles(published_at: str | None) -> list[str]:
    roles = ["durable_style", "historical_context"]
    if current_form_allowed(published_at):
        roles.insert(0, "current_form")
    else:
        roles.append("not_current_form")
    return roles
