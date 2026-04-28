"""Resilience configuration for PlayStealth CLI.

This is the single source of truth for resilience tuning. It carries:

* The legacy CLI-driven flags (``auto_report``, ``fail_fast``,
  ``no_issue_dedup``) consumed by :mod:`resilience_wrapper`.
* The extended runtime tuning (retries, timeouts, circuit breaker, telemetry,
  auto-heal, GitHub reporting) introduced for the v1.0 Resilience Engine.

Both surfaces are merged into one dataclass so callers do not have to juggle
multiple config objects.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional


def _truthy(value: Any) -> bool:
    """Parse common truthy string representations."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y", "on"}


def _falsy(value: Any) -> bool:
    """Inverse of :func:`_truthy` for flags that default to *enabled* unless
    explicitly disabled (e.g. ``PLAYSTEALTH_TELEMETRY``)."""
    if isinstance(value, bool):
        return not value
    if value is None or value == "":
        return False
    return str(value).strip().lower() in {"false", "0", "no", "n", "off"}


@dataclass
class ResilienceConfig:
    """Configuration for resilience features.

    Legacy ``auto_report`` / ``fail_fast`` / ``no_issue_dedup`` flags remain
    first for backwards compatibility with existing call sites.
    """

    # --- Legacy CLI-driven flags (consumed by resilience_wrapper) ----------
    auto_report: bool = True
    fail_fast: bool = False
    no_issue_dedup: bool = False

    # --- Retry settings ----------------------------------------------------
    max_retries: int = 3
    retry_delay_base: float = 1.0
    retry_delay_max: float = 10.0

    # --- Timeout settings (Playwright friendly, ms) ------------------------
    navigation_timeout: int = 30000
    action_timeout: int = 15000
    request_timeout: int = 60000

    # --- Fallback / smart resolver ----------------------------------------
    enable_fallback_selectors: bool = True
    enable_smart_resolver: bool = True

    # --- Circuit breaker ---------------------------------------------------
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_timeout: int = 60

    # --- GitHub reporting / auto-heal -------------------------------------
    enable_github_reporting: bool = False
    enable_auto_heal: bool = False

    # --- Telemetry ---------------------------------------------------------
    enable_telemetry: bool = True
    telemetry_batch_size: int = 10

    # ---------------------------------------------------------------------
    # Construction helpers
    # ---------------------------------------------------------------------
    @classmethod
    def from_env_or_args(cls, args: Optional[Any] = None) -> "ResilienceConfig":
        """Build a config from environment variables, with optional override
        from a parsed ``argparse.Namespace`` (or any object with attributes).

        Environment variables always win over CLI args - the deployment env
        is considered authoritative for production tuning.
        """

        def _arg(name: str, default: Any) -> Any:
            if args is None:
                return default
            return getattr(args, name, default)

        def _int_env(name: str, fallback: int) -> int:
            raw = os.getenv(name)
            if raw is None or raw == "":
                return fallback
            try:
                return int(raw)
            except ValueError:
                return fallback

        # Legacy bool flags - tolerate both env vars and argparse attrs.
        auto_report = _truthy(
            os.getenv(
                "PLAYSTEALTH_AUTO_REPORT",
                _arg("auto_report", "true"),
            )
        )
        fail_fast = _truthy(
            os.getenv(
                "PLAYSTEALTH_FAIL_FAST",
                _arg("fail_fast", "false"),
            )
        )
        no_issue_dedup = _truthy(
            os.getenv(
                "PLAYSTEALTH_NO_ISSUE_DEDUP",
                _arg("no_issue_dedup", "false"),
            )
        )

        # Telemetry defaults to ON; only an explicit falsy value disables it.
        telemetry_raw = os.getenv("PLAYSTEALTH_TELEMETRY", "")
        enable_telemetry = not _falsy(telemetry_raw)

        return cls(
            auto_report=auto_report,
            fail_fast=fail_fast,
            no_issue_dedup=no_issue_dedup,
            max_retries=_int_env(
                "PLAYSTEALTH_MAX_RETRIES",
                int(_arg("max_retries", 3) or 3),
            ),
            navigation_timeout=_int_env("PLAYSTEALTH_NAV_TIMEOUT", 30000),
            action_timeout=_int_env("PLAYSTEALTH_ACTION_TIMEOUT", 15000),
            request_timeout=_int_env("PLAYSTEALTH_REQUEST_TIMEOUT", 60000),
            enable_github_reporting=os.getenv("GITHUB_APP_ID") is not None,
            enable_auto_heal=_truthy(os.getenv("PLAYSTEALTH_AUTO_HEAL", "false")),
            enable_telemetry=enable_telemetry,
        )


# ---------------------------------------------------------------------------
# Module-level singleton helpers (kept for backwards compatibility).
# ---------------------------------------------------------------------------
_global_config: Optional[ResilienceConfig] = None


def set_global_config(cfg: ResilienceConfig) -> None:
    """Set the process-wide resilience configuration."""
    global _global_config
    _global_config = cfg


def get_global_config() -> ResilienceConfig:
    """Return the process-wide resilience configuration, lazily creating a
    default instance on first access."""
    global _global_config
    if _global_config is None:
        _global_config = ResilienceConfig()
    return _global_config
