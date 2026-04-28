"""GitHub Issue Reporter for the PlayStealth Resilience Engine.

Auto-files an issue against the GitHub App when a module fails. Supports both
ways of supplying the app's private key:

* ``GITHUB_APP_PRIVATE_KEY``      - PEM contents inline (preferred, secret-
  manager friendly).
* ``GITHUB_APP_PRIVATE_KEY_PATH`` - path to a PEM file on disk (legacy).

Either ``GITHUB_INSTALLATION_ID`` or ``GITHUB_APP_INSTALLATION_ID`` is
accepted for the installation id, again to remain backwards compatible with
older deployments.
"""
from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set


# Body section markers - kept as module-level constants so test fixtures and
# downstream tooling can rely on them being stable.
ERROR_SECTION = "### Error Message"
TRACEBACK_SECTION = "### Traceback"
META_SECTION = "### Context"

# Hard caps applied to user-controlled strings before they're sent to GitHub.
# GitHub itself caps issue bodies at 65536 chars, but keeping each section
# bounded makes for readable issues and predictable dedup hashes.
MAX_ERROR_CHARS = 2000
MAX_TRACEBACK_CHARS = 3000


class GitHubIssueReporter:
    """Auto-report module failures to GitHub Issues via a GitHub App."""

    def __init__(self) -> None:
        self.app_id: Optional[str] = os.getenv("GITHUB_APP_ID")

        # Private key: inline PEM wins, fall back to file path.
        self._private_key: Optional[str] = os.getenv("GITHUB_APP_PRIVATE_KEY")
        self.private_key_path: Optional[str] = os.getenv(
            "GITHUB_APP_PRIVATE_KEY_PATH"
        )

        # Installation id: both env-var spellings are honoured.
        self.installation_id: Optional[str] = os.getenv(
            "GITHUB_INSTALLATION_ID"
        ) or os.getenv("GITHUB_APP_INSTALLATION_ID")

        self.repo_owner: str = os.getenv("GITHUB_REPO_OWNER", "SIN-CLIs")
        self.repo_name: str = os.getenv("GITHUB_REPO_NAME", "playstealth-cli")

        # Token cache. ``_token`` is the canonical slot used by
        # ``_get_installation_token``; ``_token_cache`` is exposed as a
        # documented alias so external test fixtures can prime it.
        self._token: Optional[str] = None
        self._token_cache: Optional[str] = None
        self._token_expires: float = 0.0

        # ``_issue_hashes`` is the public dedup set used by tests; the
        # legacy code referenced ``_reported_hashes`` - keep both names
        # pointing at the same set so existing call-sites keep working.
        self._issue_hashes: Set[str] = set()
        self._reported_hashes: Set[str] = self._issue_hashes

        self._enabled: bool = bool(
            self.app_id
            and (self._private_key or self.private_key_path)
            and self.installation_id
        )

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------
    def _load_private_key(self) -> str:
        if self._private_key:
            return self._private_key
        if not self.private_key_path:
            raise ValueError(
                "Neither GITHUB_APP_PRIVATE_KEY nor "
                "GITHUB_APP_PRIVATE_KEY_PATH is set"
            )
        return Path(self.private_key_path).read_text()

    def _generate_jwt(self) -> str:
        # Imported lazily so test-suites and CLI commands that never report
        # do not require the optional ``PyJWT[crypto]`` dependency.
        import jwt  # type: ignore[import-untyped]

        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 540, "iss": self.app_id}
        return jwt.encode(payload, self._load_private_key(), algorithm="RS256")

    async def _get_installation_token(self) -> Optional[str]:
        """Return a cached installation access token, refreshing as needed."""
        # Prefer the explicit cache slot, fall back to the alias for tests
        # that prime ``_token_cache`` directly.
        cached = self._token or self._token_cache
        if cached and time.time() < self._token_expires:
            return cached

        try:
            import httpx  # local import keeps cold-start light

            app_jwt = self._generate_jwt()
            url = (
                "https://api.github.com/app/installations/"
                f"{self.installation_id}/access_tokens"
            )
            headers = {
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github.v3+json",
            }
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.post(url, headers=headers)
                if res.status_code == 201:
                    data = res.json()
                    self._token = data["token"]
                    self._token_cache = self._token
                    # Tokens last 1h; refresh ~10 min early.
                    self._token_expires = time.time() + 3000
                    return self._token
                # Surface the failure for callers / logging.
                print(
                    f"github_issue_reporter: token request failed "
                    f"({res.status_code}): {res.text[:200]}"
                )
        except Exception as exc:  # pragma: no cover - defensive
            print(f"github_issue_reporter: token fetch exception: {exc}")

        return None

    # ------------------------------------------------------------------
    # Body / dedup helpers
    # ------------------------------------------------------------------
    def _dedup_hash(self, module: str, error: str) -> str:
        """Stable per-day hash for issue deduplication."""
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return hashlib.sha256(
            f"{module}:{error}:{day}".encode()
        ).hexdigest()[:12]

    def _build_title(self, module_name: str, error_msg: str, severity: str) -> str:
        # Headline icon + uppercase severity + module path + truncated error.
        return (
            f"\U0001F6A8 {severity.upper()}: [{module_name}] "
            f"{error_msg[:80]}"
        ).rstrip()

    def _build_body(
        self,
        *,
        module_name: str,
        error_msg: str,
        traceback_str: str,
        session_id: str,
        severity: str,
        critical: bool,
    ) -> str:
        # Apply hard caps before rendering.
        error_clipped = error_msg[:MAX_ERROR_CHARS]
        if len(error_msg) > MAX_ERROR_CHARS:
            error_clipped += "\n... (truncated)"
        tb_clipped = traceback_str[:MAX_TRACEBACK_CHARS]
        if len(traceback_str) > MAX_TRACEBACK_CHARS:
            tb_clipped += "\n... (truncated)"

        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        return (
            f"{META_SECTION}\n"
            f"- **Module:** `{module_name}`\n"
            f"- **Session:** `{session_id}`\n"
            f"- **Severity:** `{severity}`\n"
            f"- **Critical:** `{'yes' if critical else 'no'}`\n"
            f"- **Timestamp:** `{ts}`\n\n"
            f"{ERROR_SECTION}\n"
            "```\n"
            f"{error_clipped}\n"
            "```\n\n"
            f"{TRACEBACK_SECTION}\n"
            "```python\n"
            f"{tb_clipped}\n"
            "```\n\n"
            "> Auto-reported by the PlayStealth Resilience Engine. "
            "Fallback applied. Telemetry logged.\n"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def create_issue(
        self,
        module_name: str,
        error_msg: str,
        traceback_str: str,
        session_id: str = "unknown",
        critical: bool = False,
        no_dedup: bool = False,
        severity: str = "high",
        labels: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Create a GitHub issue for a module failure.

        Returns the new issue's ``html_url`` on success, otherwise ``None``.
        """
        if not self._enabled:
            return None

        if critical and severity == "high":
            # Critical failures escalate the severity label automatically.
            severity = "critical"

        h = self._dedup_hash(module_name, error_msg)
        if not no_dedup and h in self._issue_hashes:
            return None
        # Track the hash up front so concurrent reporters dedup correctly.
        self._issue_hashes.add(h)

        title = self._build_title(module_name, error_msg, severity)
        body = self._build_body(
            module_name=module_name,
            error_msg=error_msg,
            traceback_str=traceback_str,
            session_id=session_id,
            severity=severity,
            critical=critical,
        )

        # Default + caller-provided labels, deduplicated while preserving
        # insertion order.
        merged_labels: List[str] = []
        for lbl in (
            "bug",
            "auto-generated",
            f"severity:{severity}",
            *(labels or ()),
        ):
            if lbl and lbl not in merged_labels:
                merged_labels.append(lbl)

        try:
            import httpx

            token = await self._get_installation_token()
            if not token:
                return None
            url = (
                f"https://api.github.com/repos/{self.repo_owner}/"
                f"{self.repo_name}/issues"
            )
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            async with httpx.AsyncClient(timeout=15) as client:
                res = await client.post(
                    url,
                    json={
                        "title": title,
                        "body": body,
                        "labels": merged_labels,
                    },
                    headers=headers,
                )
                if res.status_code == 201:
                    return res.json().get("html_url")
                print(
                    "github_issue_reporter: create_issue failed "
                    f"({res.status_code}): {res.text[:200]}"
                )
        except Exception as exc:  # pragma: no cover - defensive
            print(f"github_issue_reporter: create_issue exception: {exc}")

        return None
