"""Onboarding wizard for `playstealth init`.

A first-run helper that:

1. creates the local state directory (`.playstealth_state/` by default)
2. writes a default persona if none exists
3. seeds a `.env` from `.env.example` if there is no `.env` yet
4. checks that Playwright's chromium is installed and prints the install
   command if it isn't
5. prints the next-step commands the user should run

The wizard is non-interactive by default (idempotent, safe to re-run in
CI) and prompts only when stdin is a TTY and the caller didn't pass
`--non-interactive`.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from playstealth_actions.persona_manager import (
    DEFAULT_PERSONA,
    create_persona,
    load_personas,
)


def _state_dir() -> Path:
    return Path(os.getenv("PLAYSTEALTH_STATE_DIR", ".playstealth_state"))


def _print_step(idx: int, total: int, label: str) -> None:
    print(f"[{idx}/{total}] {label}")


def _ensure_state_dir() -> Path:
    sd = _state_dir()
    sd.mkdir(parents=True, exist_ok=True)
    return sd


def _ensure_default_persona() -> bool:
    """Return True if a persona was created, False if one already existed."""
    personas = load_personas()
    # load_personas() always returns at least {"default": DEFAULT_PERSONA},
    # but the file on disk may not exist yet — we only count file-backed
    # personas as "already there".
    if (_state_dir() / "personas.json").exists():
        return False
    create_persona("default", **DEFAULT_PERSONA)
    return True


def _ensure_env_file(project_root: Path) -> tuple[bool, str]:
    """Copy .env.example -> .env if .env is missing.

    Returns (created, message).
    """
    env = project_root / ".env"
    example = project_root / ".env.example"
    if env.exists():
        return False, f".env already present at {env}"
    if not example.exists():
        return False, "no .env.example found; skipping (manual config required)"
    shutil.copy(example, env)
    return True, f"copied .env.example -> {env}"


def _check_playwright_chromium() -> tuple[bool, str]:
    """Return (installed, message). Never raises."""
    try:
        import importlib

        importlib.import_module("playwright")
    except ImportError:
        return False, "playwright is not installed; run `pip install playwright`"

    cache = Path.home() / ".cache" / "ms-playwright"
    if cache.exists() and any(cache.glob("chromium-*")):
        return True, f"chromium present in {cache}"
    return False, "chromium not installed; run `python -m playwright install chromium`"


def _print_next_steps(env_created: bool) -> None:
    print()
    print("Next steps:")
    if env_created:
        print("  1. Open .env and set the values you actually need.")
    print("  2. Try a smoke run:")
    print("       playstealth diagnose benchmark")
    print("  3. List the survey queue:")
    print("       playstealth queue list")
    print("  4. Read the docs:")
    print("       cat README.md")


def run_init_wizard(
    project_root: Path | None = None,
    *,
    non_interactive: bool = False,
    out: Iterable[str] | None = None,
) -> int:
    """Execute the init wizard. Returns 0 on success, non-zero on failure."""
    root = (project_root or Path.cwd()).resolve()
    print(f"PlayStealth init wizard\n  project: {root}\n")

    total = 4
    _print_step(1, total, "Ensuring state directory")
    sd = _ensure_state_dir()
    print(f"      -> {sd}")

    _print_step(2, total, "Ensuring default persona")
    created = _ensure_default_persona()
    print(f"      -> {'created' if created else 'already present'}")

    _print_step(3, total, "Seeding .env from .env.example")
    env_created, msg = _ensure_env_file(root)
    print(f"      -> {msg}")

    _print_step(4, total, "Checking Playwright chromium")
    ok, msg = _check_playwright_chromium()
    print(f"      -> {msg}")

    _print_next_steps(env_created)
    return 0 if ok else 0  # never fail the wizard for missing browser; we report it.


def cli() -> int:
    parser = argparse.ArgumentParser(prog="playstealth init", description=__doc__)
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Never prompt; useful in CI and Dockerfiles.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Treat this directory as the project root (default: cwd)",
    )
    args = parser.parse_args()
    return run_init_wizard(
        project_root=args.project_root,
        non_interactive=args.non_interactive,
    )


if __name__ == "__main__":
    sys.exit(cli())
