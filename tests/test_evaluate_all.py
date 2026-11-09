# -*- coding: utf-8 -*-

"""The Energy step's use of seamm_exec's Evaluator, with a fake Evaluator:
keys, duplicate selections, failures, and the report."""

import types

import numpy as np
import pytest

import seamm_exec
from seamm_exec import EvaluatorResult

from energy_step.energy import Energy


class FakeEvaluator:
    submitted = []
    plan = {}  # key -> EvaluatorResult kwargs

    def __init__(self, node, mc, properties=(), name=None):
        FakeEvaluator.submitted = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def submit(self, configuration, key=None, options=None):
        FakeEvaluator.submitted.append(key)
        return key

    @staticmethod
    def topology_key(configuration, options=None):
        return (configuration.n_atoms,)

    def results(self):
        # Out of order, as tasks finish
        for key in reversed(FakeEvaluator.submitted):
            kwargs = {"ok": True, "energy": -1.0, "path": "batch"}
            kwargs.update(FakeEvaluator.plan.get(key, {}))
            if kwargs["ok"] and "gradients" not in kwargs:
                kwargs["gradients"] = np.zeros((1, 3))
            yield EvaluatorResult(key=key, **kwargs)


def _configuration(id_, name):
    return types.SimpleNamespace(id=id_, name=name, n_atoms=1)


@pytest.fixture
def me(monkeypatch):
    monkeypatch.setattr(seamm_exec, "Evaluator", FakeEvaluator)
    stored = []
    records = []
    node = types.SimpleNamespace(
        _store=lambda configuration, data, gradients, stress: stored.append(
            (configuration.id, data["energy"])
        ),
        _store_calculation_record=lambda configuration, result: records.append(
            (configuration.id, (result.data or {}).get("calculation"))
        ),
    )
    node.stored = stored
    node.records = records
    return node


def test_keys_are_configuration_ids_and_duplicates_run_once(me):
    a, b = _configuration(4, "a"), _configuration(9, "b")
    rows, failed, counts = Energy._evaluate_all(
        me, {"level": "X"}, [a, b, a], ["energy", "gradients"], True, False
    )
    assert FakeEvaluator.submitted == ["c4", "c9"]
    assert sorted(i for i, _, _ in rows) == [0, 1]  # mapped back by key
    assert counts["tasks"] == 2 and counts["mdi"] == 0
    # A rerun submits the same keys, so the task layer finds them
    Energy._evaluate_all(me, {"level": "X"}, [a, b], ["energy"], False, False)
    assert FakeEvaluator.submitted == ["c4", "c9"]


def test_failures_are_listed_after_the_others_are_stored(me):
    FakeEvaluator.plan = {"c2": {"ok": False, "energy": None, "reason": "boom"}}
    try:
        configurations = [_configuration(1, "one"), _configuration(2, "two")]
        rows, failed, counts = Energy._evaluate_all(
            me, {"level": "X"}, configurations, ["energy"], False, False
        )
    finally:
        FakeEvaluator.plan = {}
    assert me.stored == [(1, -1.0)]
    assert [(c.name, r) for c, r in failed] == [("two", "boom")]
    with pytest.raises(RuntimeError, match="(?s)1 of 2 structures.*two: boom"):
        Energy._report_failures(failed, 2)
    Energy._report_failures([], 2)  # nothing to say


def test_the_report_says_how():
    assert Energy._how({"mdi": 3, "tasks": 0, "restored": 0, "engines": 1}) == (
        "using 1 engine session"
    )
    assert Energy._how({"mdi": 0, "tasks": 5, "restored": 2, "engines": 0}) == (
        "as 5 separate calculations, 2 of them finished in an earlier run"
    )
    assert Energy._how({"mdi": 1, "tasks": 4, "restored": 0, "engines": 1}) == (
        "1 over MDI in 1 engine session and 4 as separate calculations"
    )


def test_calculation_records_are_passed_on(me):
    FakeEvaluator.plan = {"c3": {"data": {"calculation": {"fingerprint": "fp"}}}}
    try:
        Energy._evaluate_all(
            me, {"level": "X"}, [_configuration(3, "a")], ["energy"], False, False
        )
    finally:
        FakeEvaluator.plan = {}
    assert me.records == [(3, {"fingerprint": "fp"})]


def test_store_calculation_record(tmp_path):
    """The settings fingerprint and the record become properties of the
    configuration, named like the energy, for a store's harvest."""
    molsystem = pytest.importorskip("molsystem")
    db = molsystem.SystemDB(filename=f"file:{tmp_path / 'seamm.db'}")
    try:
        configuration = db.create_system(name="w").create_configuration()
        configuration.from_smiles("O")
        node = types.SimpleNamespace(model="ORCA:DFT@X/def2-SVP")
        record = {
            "program": "ORCA",
            "fingerprint": "sha256:abc",
            "geometry fingerprint": "sha256:geo",
        }
        Energy._store_calculation_record(
            node,
            configuration,
            EvaluatorResult(
                key="c1", ok=True, energy=-1.0, data={"calculation": record}
            ),
        )
        p = configuration.properties
        name = "settings fingerprint#Energy#ORCA:DFT@X/def2-SVP"
        assert p.get(name)[name]["value"] == "sha256:abc"
        name = "calculation#Energy#ORCA:DFT@X/def2-SVP"
        assert p.get(name)[name]["value"]["geometry fingerprint"] == "sha256:geo"
        # No record (e.g. an engine without fingerprints): nothing stored
        other = db.create_system(name="x").create_configuration()
        Energy._store_calculation_record(
            node, other, EvaluatorResult(key="c2", ok=True, energy=-1.0)
        )
        assert not other.properties.get("settings fingerprint#*")
    finally:
        db.close()
