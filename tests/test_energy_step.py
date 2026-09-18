#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `energy_step` package."""

import pytest  # noqa: F401
import energy_step  # noqa: F401


def test_construction():
    """Just create an object and test its type."""
    result = energy_step.Energy()
    assert str(type(result)) == "<class 'energy_step.energy.Energy'>"
