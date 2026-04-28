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

        self._token: Optional[str] = None
        self._token_expires: float = 0.0

        # Public alias kept for the existing wrapper code.
        self._reported_hashes: Set[str] = set()
        # Alias used by the new test-suite.
        self._issue_hashes: Set[str] = self._reported_hashes
        self._token_cache: Optional[str] = None  # documented attribute

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
        if self._token and time.time() < self._token_expires:
            return self._token

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
                    # Tokens last 1h; refresh ~10 min early.
                    self._token_expires = time.time() + 3000
                    self._token_cache = self._token
                    return self._token
                # surface the failure for callers / logging
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
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return hashlib.sha256(
            f"{module}:{error}:{day}".encode()
        ).hexdigest()[:12]

    def _get_template_type(self, module_name: str, error_msg: str) -> str:
        ctx = f"{module_name} {error_msg}".lower()
        keywords = (
            "selector",
            "dom",
            "scan",
            "click",
            "resolve",
            "locator",
            "timeout",
            "visible",
        )
        if any(kw in ctx for kw in keywords):
            return "selector_update"
        return "bug_report"

    # Body section markers used by the test suite & docs.
    # Keep these stable -- downstream tooling greps for them.
    _ERROR_MSG_HEADER = "### Error Message"
    _TRACEBACK_HEADER = "### Traceback"
    _MAX_ERROR_CHARS = 2000
    _MAX_TRACEBACK_CHARS = 3000

    def _format_body(
        self,
        template: str,
        module_name: str,
        error_msg: str,
        tb: str,
        sid: str,
        critical: bool,
        severity: str = "high",
    ) -> str:
        truncated_error = error_msg[: self._MAX_ERROR_CHARS]
        truncated_tb = tb[: self._MAX_TRACEBACK_CHARS]
        base = (
            f"### Module: `{module_name}`
"
            f"**Severity:** `{severity}`
"
            f"**Session:** `{sid}`
"
            f"**Critical:** `{'Yes' if critical else 'No'}`
"
            f"**Timestamp:** `{datetime.now(timezone.utc).isoformat()}Z`

"
            f"{self._ERROR_MSG_HEADER}
"
            "```
"
            f"{truncated_error}
"
            "```

"
            f"{self._TRACEBACK_HEADER}
"
            "```python
"
            f"{truncated_tb}
"
            "```
"
        )
        if template == "selector_update":
            return base + (
                "
### Selector / DOM context
"
                "- [ ] Verify the target platform's DOM has not changed
"
                "- [ ] Validate CSS / XPath / text heuristics with "
                "`playstealth profile <url>`
"
                "- [ ] Adjust fallback selectors in `smart_selector.py` or "
                "the relevant plugin
"
                "- [ ] Consider `playstealth queue blacklist-add` for a "
                "persistent platform change

"
                "> Auto-reported by the PlayStealth Resilience Engine. "
                "Fallback applied. Telemetry logged.
"
            )
        return base + (
            "
### Bug context
"
            "- [ ] Check network / proxy state and Playwright binary version
"
            "- [ ] Validate `.env` secrets and GitHub App permissions
"
            "- [ ] Inspect `telemetry.jsonl` for preceding module failures
"
            "- [ ] On state / resume errors: clean `.playstealth_state/` "
            "and restart

"
            "> Auto-reported by the PlayStealth Resilience Engine. "
            "Fallback applied. Telemetry logged.
"
        )
        return base + (
            "\n### Bug context\n"
            "- [ ] Check network / proxy state and Playwright binary version\n"
            "- [ ] Validate `.env` secrets and GitHub App permissions\n"
            "- [ ] Inspect `telemetry.jsonl` for preceding module failures\n"
            "- [ ] On state / resume errors: clean `.playstealth_state/` "
            "and restart\n\n"
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

        h = self._dedup_hash(module_name, error_msg)
        if not no_dedup and h in self._reported_hashes:
            return None
        self._reported_hashes.add(h)

        template = self._get_template_type(module_name, error_msg)
        # Title contract: "🚨 <SEVERITY>: [<module>] <short-error>"
        # The first segment is grepped by alerting tools; do not change.
        short_err = error_msg.replace("\n", " ")[:80] or "<no error message>"
        title = (
            f"🚨 {severity.upper()}: [{module_name}] {short_err}"
        )
        default_labels = [
            "bug",
            "auto-generated",
            f"severity:{severity}",
            module_name.split(".")[0],
            template,
        ]
        if critical:
            default_labels.append("critical")
        if labels:
            default_labels.extend(labels)

        body = self._format_body(
            template,
            module_name,
            error_msg,
            traceback_str,
            session_id,
            critical,
            severity=severity,
        )

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
                        "labels": default_labels,
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
