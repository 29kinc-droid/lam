from __future__ import annotations

import pytest

from lam.tools.calculator import calculate


def test_calculate_basic_arithmetic() -> None:
    assert calculate({"expression": "3 * (4 + 5)"}) == "27.0"


def test_calculate_negative_and_power() -> None:
    assert calculate({"expression": "-2 ** 3"}) == "-8.0"


def test_calculate_rejects_unsupported_expression() -> None:
    with pytest.raises(ValueError):
        calculate({"expression": "__import__('os')"})
