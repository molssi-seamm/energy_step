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


@pytest.fixture()
def system():
    confs = [_conf("water 1"), _conf("water 2"), _conf("dimer 1", (8, 1, 1, 8, 1, 1))]
    return SimpleNamespace(configurations=confs, configuration=confs[1])


# --------------------------------------------------------------------------- #
# _select_configurations / _structure_pool
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "how, name, expected",
    [
        ("all", "", ["water 1", "water 2", "dimer 1"]),
        ("first", "", ["water 1"]),
        ("last", "", ["dimer 1"]),
        ("name is", "water 2", ["water 2"]),
        ("name matches", "water*", ["water 1", "water 2"]),
        ("name regexp", r"^dimer \d", ["dimer 1"]),
    ],
)
def test_select_configurations(node, system, how, name, expected):
    result = node._select_configurations(system, how, name)
    assert [c.name for c in result] == expected


def test_select_configurations_unknown_selector(node, system):
    with pytest.raises(ValueError):
        node._select_configurations(system, "bogus", "")


def test_structure_pool_current(node, system):
    system_db = SimpleNamespace(system=system, get_system=lambda n: system)
    P = {
        "structure": "current",
        "structure configurations": "current",
        "structure configuration name": "",
    }
    assert [c.name for c in node._structure_pool(P, system_db)] == ["water 2"]


def test_structure_pool_named_system_all(node, system):
    seen = {}

    def get_system(name):
        seen["name"] = name
        return system

    system_db = SimpleNamespace(system=None, get_system=get_system)
    P = {
        "structure": "ensemble",
        "structure configurations": "all",
        "structure configuration name": "",
    }
    result = node._structure_pool(P, system_db)
    assert seen["name"] == "ensemble"
    assert len(result) == 3


def test_structure_pool_list_variable(node):
    confs = [_conf("a"), _conf("b")]
    P = {
        "structure": confs,
        "structure configurations": "first",  # ignored for a list
        "structure configuration name": "",
    }
    assert node._structure_pool(P, None) == confs


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
        "structure": "current",
        "structure configurations": "all",
        "structure configuration name": "",
        "gradients": "yes",
        "stress": "no",
    }
    text = node.description_text(P)
    assert "energy and gradients" in text
    assert "every configuration" in text


def test_description_text_energy_only(node):
    P = {
        "structure": "clusters",
        "structure configurations": "name matches",
        "structure configuration name": "tetramer*",
        "gradients": "no",
        "stress": "no",
    }
    text = node.description_text(P)
    assert "gradients" not in text
    assert "clusters" in text and "tetramer*" in text
