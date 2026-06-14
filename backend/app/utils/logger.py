"""Logging and monitoring setup."""

import sys

from loguru import logger

from app.config import Settings


def configure_logging(level: str) -> None:
    """Configure Loguru output."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=level.upper(),
        backtrace=False,
        diagnose=False,
    )


def configure_sentry(settings: Settings) -> None:
    """Initialize Sentry when a DSN is configured."""
    if settings.sentry_dsn is None:
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[FastApiIntegration()],
        traces_sample_rate=settings.sentry_traces_sample_rate,
    )


__all__ = ["configure_logging", "configure_sentry"]
