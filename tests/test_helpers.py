# -*- coding: utf-8 -*-

"""Tests for the selection, grouping and launch helpers of the Energy node."""

from types import SimpleNamespace

import pytest

from energy_step.energy import Energy


@pytest.fixture(scope="module")
def node():
    node = Energy()
    node._id = ("1",)  # so the output header can be built outside a flowchart
    return node


def _conf(name, numbers=(8, 1, 1), charge=0, multiplicity=1, periodicity=0):
    return SimpleNamespace(
        name=name,
        atoms=SimpleNamespace(atomic_numbers=list(numbers)),
        charge=charge,
        spin_multiplicity=multiplicity,
        periodicity=periodicity,
    )


# --------------------------------------------------------------------------- #
# Grouping into engine sessions
# --------------------------------------------------------------------------- #
def test_topology_key_groups_same_composition(node):
    a = _conf("a")
    b = _conf("b")
    assert node._topology_key(a) == node._topology_key(b)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"numbers": (8, 1, 1, 8, 1, 1)},
        {"charge": 1},
        {"multiplicity": 3},
        {"periodicity": 3},
        {"numbers": (1, 1, 8)},  # same atoms, different order -> different session
    ],
)
def test_topology_key_distinguishes(node, kwargs):
    assert node._topology_key(_conf("a")) != node._topology_key(_conf("b", **kwargs))


# --------------------------------------------------------------------------- #
# Launch arguments from the model chemistry
# --------------------------------------------------------------------------- #
def test_mdi_method_and_basis_prefers_engine_args(node):
    mc = {"method": "B3LYP", "basis": "def2-SVP"}
    options = {"mdi_method_arg": "B3LYP-D4", "mdi_basis_arg": "def2-TZVP"}
    assert node._mdi_method_and_basis(mc, options) == ("B3LYP-D4", "def2-TZVP")


def test_mdi_method_and_basis_falls_back_to_level(node):
    mc = {"method": "PM6-ORG", "basis": None}
    assert node._mdi_method_and_basis(mc, {}) == ("PM6-ORG", None)


def test_mdi_method_and_basis_user_basis(node):
    mc = {"method": "B3LYP", "basis": "cc-pVTZ"}
    options = {"mdi_method_arg": "B3LYP"}
    assert node._mdi_method_and_basis(mc, options) == ("B3LYP", "cc-pVTZ")


@pytest.mark.parametrize(
    "value, expected",
    [(True, True), ("yes", True), ("Yes", True), ("no", False), (False, False)],
)
def test_truthy(node, value, expected):
    assert node._truthy(value) is expected


# --------------------------------------------------------------------------- #
# Description
# --------------------------------------------------------------------------- #
def test_description_text_mentions_gradients(node):
    P = {
        "source systems": "current",
        "source system name": "",
        "source configurations": "all",
        "source configuration name": "",
        "gradients": "yes",
        "stress": "no",
    }
    text = " ".join(node.description_text(P).split())  # undo the line wrapping
    assert "energy and gradients" in text
    assert "all configurations of the current system" in text
    assert "REF_forces" in text


def test_description_text_energy_only(node):
    P = {
        "source systems": "name is",
        "source system name": "clusters",
        "source configurations": "name matches",
        "source configuration name": "tetramer*",
        "gradients": "no",
        "stress": "no",
    }
    text = " ".join(node.description_text(P).split())
    assert "gradients" not in text and "REF_forces" not in text
    assert "clusters" in text and "tetramer*" in text
