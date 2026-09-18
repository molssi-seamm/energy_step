# -*- coding: utf-8 -*-

"""Tests of the Energy step parameters and metadata."""

import energy_step


def test_parameter_defaults():
    P = energy_step.EnergyParameters()
    values = P.values_to_dict()
    assert values["source systems"] == "current"
    assert values["source configurations"] == "current"
    assert values["gradients"] == "yes"
    assert values["stress"] == "yes"


def test_metadata_properties_match_csv():
    """Every property in metadata['results'] is registered in data/properties.csv."""
    import csv
    import importlib.resources

    path = importlib.resources.files("energy_step") / "data" / "properties.csv"
    with path.open() as fd:
        registered = {row["Property"] for row in csv.DictReader(fd)}
    for key, meta in energy_step.metadata["results"].items():
        if "property" in meta:
            assert meta["property"] in registered, key
