"""Unit tests for playstealth_actions.consistency_validator.

Covers async record/load round-trip, demographic-contradiction detection
(age, income, employment, education), straight-line detection, and the
600-entry rolling-window trim.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def fresh_module(tmp_path, monkeypatch):
    """Reload consistency_validator with PLAYSTEALTH_STATE_DIR isolated."""
    monkeypatch.setenv("PLAYSTEALTH_STATE_DIR", str(tmp_path / "state"))
    from playstealth_actions import consistency_validator as cv

    importlib.reload(cv)
    return cv


class TestRecordAndLoad:
    @pytest.mark.asyncio
    async def test_record_creates_file(self, fresh_module):
        await fresh_module.record_answer("How old?", "34", "survey-1")
        assert fresh_module.CONSISTENCY_FILE.exists()

    @pytest.mark.asyncio
    async def test_record_appends_to_history(self, fresh_module):
        await fresh_module.record_answer("Q1", "A1", "s1")
        await fresh_module.record_answer("Q2", "A2", "s2")
        log = fresh_module._load_log()
        assert len(log["history"]) == 2
        assert log["history"][0]["q"] == "Q1"
        assert log["history"][1]["sid"] == "s2"

    @pytest.mark.asyncio
    async def test_history_truncates_to_500_when_over_600(self, fresh_module):
        # Pre-populate so we don't make 600 awaited round-trips.
        log = {
            "history": [{"q": f"q{i}", "a": "a", "sid": "s"} for i in range(600)],
            "straight_line_flags": 0,
            "contradictions": 0,
        }
        fresh_module._save_log(log)
        await fresh_module.record_answer("trigger", "answer", "x")
        new_log = fresh_module._load_log()
        # After append we had 601 entries, the trim drops to the last 500.
        assert len(new_log["history"]) == 500
        # The most recent entry must survive.
        assert new_log["history"][-1]["q"] == "trigger"

    @pytest.mark.asyncio
    async def test_long_question_is_truncated_to_120(self, fresh_module):
        long_q = "x" * 500
        await fresh_module.record_answer(long_q, "a", "s")
        log = fresh_module._load_log()
        assert len(log["history"][0]["q"]) == 120


class TestValidateConsistency:
    @pytest.mark.asyncio
    async def test_age_within_tolerance_is_consistent(self, fresh_module):
        result = await fresh_module.validate_consistency(
            "Wie alt sind Sie?", "33 Jahre", {"age": 34}
        )
        assert result["consistent"] is True
        assert result["contradictions"] == []

    @pytest.mark.asyncio
    async def test_age_outside_tolerance_flags_contradiction(self, fresh_module):
        result = await fresh_module.validate_consistency(
            "Wie alt sind Sie?", "55 Jahre", {"age": 34}
        )
        assert result["consistent"] is False
        assert any("Age" in c for c in result["contradictions"])

    @pytest.mark.asyncio
    async def test_employment_mismatch_flags_contradiction(self, fresh_module):
        result = await fresh_module.validate_consistency(
            "Was ist Ihr Beruf?",
            "Arbeitslos",
            {"employment": "Full-time"},
        )
        assert result["consistent"] is False
        assert any("Employment" in c for c in result["contradictions"])

    @pytest.mark.asyncio
    async def test_education_match_is_consistent(self, fresh_module):
        result = await fresh_module.validate_consistency(
            "Höchster Bildungsabschluss?",
            "Bachelor of Science",
            {"education": "Bachelor"},
        )
        assert result["consistent"] is True

    @pytest.mark.asyncio
    async def test_unrelated_question_is_consistent(self, fresh_module):
        result = await fresh_module.validate_consistency(
            "Welche Farbe mögen Sie?",
            "Blau",
            {"age": 30, "education": "Bachelor"},
        )
        assert result["consistent"] is True

    @pytest.mark.asyncio
    async def test_income_keyword_match(self, fresh_module):
        result = await fresh_module.validate_consistency(
            "Monatliches Einkommen?",
            "3000-4000 Euro",
            {"income_bracket": "3000-4000"},
        )
        assert result["consistent"] is True


class TestStraightLining:
    @pytest.mark.asyncio
    async def test_four_identical_answers_flags_true(self, fresh_module):
        result = await fresh_module.detect_straight_lining(
            ["3", "3", "3", "3"], threshold=4
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_varied_answers_flag_false(self, fresh_module):
        result = await fresh_module.detect_straight_lining(
            ["1", "2", "3", "4"], threshold=4
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_below_threshold_returns_false(self, fresh_module):
        result = await fresh_module.detect_straight_lining(["3", "3"], threshold=4)
        assert result is False

    @pytest.mark.asyncio
    async def test_only_last_n_are_considered(self, fresh_module):
        # First three differ, last four are identical -> straight line on tail.
        result = await fresh_module.detect_straight_lining(
            ["1", "2", "3", "5", "5", "5", "5"], threshold=4
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self, fresh_module):
        result = await fresh_module.detect_straight_lining(
            ["Yes", "YES", "yes", "yes "], threshold=4
        )
        assert result is True
