"""Unit tests for playstealth_actions.answer_strategies.

Covers all three strategies (Random, Consistent, Persona), the heuristic
matcher, and the get_strategy() factory. PersonaStrategy is exercised with
both deterministic-fallback and explicit-heuristic paths.
"""

from __future__ import annotations

import pytest

from playstealth_actions.answer_strategies import (
    BaseStrategy,
    ConsistentStrategy,
    PersonaStrategy,
    RandomStrategy,
    _persona_heuristic_indices,
    get_strategy,
)
from playstealth_actions.persona_manager import DEFAULT_PERSONA


class TestRandomStrategy:
    @pytest.mark.asyncio
    async def test_returns_int_in_range(self):
        strategy = RandomStrategy()
        result = await strategy.choose("any question", 5, ["a", "b", "c", "d", "e"])
        assert isinstance(result, int)
        assert 0 <= result < 5

    @pytest.mark.asyncio
    async def test_zero_options_returns_zero(self):
        strategy = RandomStrategy()
        result = await strategy.choose("?", 0, [])
        assert result == 0


class TestConsistentStrategy:
    @pytest.mark.asyncio
    async def test_returns_fixed_index_when_in_range(self):
        strategy = ConsistentStrategy(fixed_index=2)
        result = await strategy.choose("?", 5, ["a", "b", "c", "d", "e"])
        assert result == 2

    @pytest.mark.asyncio
    async def test_clamps_to_max_when_out_of_range(self):
        strategy = ConsistentStrategy(fixed_index=99)
        result = await strategy.choose("?", 3, ["a", "b", "c"])
        assert result == 2

    @pytest.mark.asyncio
    async def test_default_index_is_one(self):
        strategy = ConsistentStrategy()
        result = await strategy.choose("?", 5, ["a", "b", "c", "d", "e"])
        assert result == 1

    @pytest.mark.asyncio
    async def test_zero_options_returns_zero(self):
        strategy = ConsistentStrategy(fixed_index=3)
        result = await strategy.choose("?", 0, [])
        assert result == 0


class TestPersonaStrategy:
    @pytest.mark.asyncio
    async def test_deterministic_fallback(self):
        # No persona heuristic matches for this question, so the
        # md5-seeded RNG fallback runs and must be reproducible.
        strategy = PersonaStrategy(persona="default")
        a = await strategy.choose("Random unrelated question", 4, ["w", "x", "y", "z"])
        b = await strategy.choose("Random unrelated question", 4, ["w", "x", "y", "z"])
        assert a == b
        assert 0 <= a < 4

    @pytest.mark.asyncio
    async def test_smoking_heuristic(self):
        strategy = PersonaStrategy(persona="default")
        options = [
            "Ich rauche täglich",
            "Ich rauche keine Zigaretten",
            "Ich rauche gelegentlich",
        ]
        result = await strategy.choose("Wie oft rauchen Sie Zigaretten?", 3, options)
        assert result == 1  # The "ich rauche keine zigaretten" option

    @pytest.mark.asyncio
    async def test_zero_options_returns_zero(self):
        strategy = PersonaStrategy()
        result = await strategy.choose("?", 0, [])
        assert result == 0

    @pytest.mark.asyncio
    async def test_loads_explicit_persona(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PLAYSTEALTH_STATE_DIR", str(tmp_path))
        # Re-import to pick up new env
        import importlib

        from playstealth_actions import persona_manager as pm

        importlib.reload(pm)
        pm.create_persona("test_user", age=99, gender="female")

        # PersonaStrategy reuses the new module's get_persona.
        from playstealth_actions import answer_strategies as ast

        importlib.reload(ast)
        strategy = ast.PersonaStrategy(persona="test_user")
        # We don't assert on the persona's age here because the reload of
        # ast happens AFTER pm.create_persona, so the strategy sees the
        # written persona. The choose() output is deterministic per hash.
        result = await strategy.choose("?", 3, ["a", "b", "c"])
        assert 0 <= result < 3


class TestPersonaHeuristic:
    def test_no_match_returns_empty(self):
        result = _persona_heuristic_indices(
            "Completely unrelated prompt", ["one", "two"], DEFAULT_PERSONA
        )
        assert result == []

    def test_gender_match(self):
        # DEFAULT_PERSONA has gender="male", which maps to "männlich"
        result = _persona_heuristic_indices(
            "Ihr Geschlecht?",
            ["weiblich", "männlich", "divers"],
            DEFAULT_PERSONA,
        )
        assert result == [1]

    def test_interests_match_top_three(self):
        # DEFAULT_PERSONA interests include tech, finance, travel, health
        result = _persona_heuristic_indices(
            "Welche Hobbies haben Sie?",
            ["Sport", "Tech & Computer", "Finance", "Cooking", "Travel"],
            DEFAULT_PERSONA,
        )
        # Returns at most 3 matching indices
        assert len(result) <= 3
        assert 1 in result  # tech
        assert 2 in result  # finance


class TestGetStrategy:
    def test_returns_random(self):
        strategy = get_strategy("random")
        assert isinstance(strategy, RandomStrategy)
        assert isinstance(strategy, BaseStrategy)

    def test_returns_consistent(self):
        strategy = get_strategy("consistent", fixed_index=3)
        assert isinstance(strategy, ConsistentStrategy)
        assert strategy.fixed_index == 3

    def test_returns_persona(self):
        strategy = get_strategy("persona", persona="default")
        assert isinstance(strategy, PersonaStrategy)
        assert strategy.persona_name == "default"

    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("does-not-exist")
