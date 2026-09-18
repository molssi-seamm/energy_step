# -*- coding: utf-8 -*-

"""This file contains metadata describing the results from the Energy step."""

metadata = {}

"""Results that the Energy step produces.

The step carries no computational model of its own -- the energy comes from the
Model Chemistry published upstream, driven over MDI -- so only ``results`` is
populated. ``{model}`` in the property names is filled from the model chemistry's
level spec at run time (e.g. ``xnn:MLFF@water`` or ``MOPAC:SQM@PM6-ORG``).

The energy, gradients and stress are *always* stored as properties on every
configuration evaluated (that is the point of the step); the entries here
additionally let the user save them, and the summary values, to variables or
tables. ``store_results`` is called once per configuration, so a table gets one
row per structure.
"""

metadata["results"] = {
    "energy": {
        "description": "The energy of the structure",
        "dimensionality": "scalar",
        "property": "energy#Energy#{model}",
        "type": "float",
        "units": "kJ/mol",
        "format": ".3f",
    },
    "gradients": {
        "description": "The gradients on the atoms",
        "dimensionality": "[n_atoms][3]",
        "property": "gradients#Energy#{model}",
        "type": "json",
        "units": "kJ/mol/Å",
        "format": ".3f",
    },
    "stress": {
        "description": "The stress tensor (periodic systems only)",
        "dimensionality": "[3][3]",
        "property": "stress#Energy#{model}",
        "type": "json",
        "units": "GPa",
        "format": ".4f",
    },
    "maximum force": {
        "description": "The largest force component on any atom",
        "dimensionality": "scalar",
        "type": "float",
        "units": "kJ/mol/Å",
        "format": ".3f",
    },
    "rms force": {
        "description": "The root-mean-square force component",
        "dimensionality": "scalar",
        "type": "float",
        "units": "kJ/mol/Å",
        "format": ".3f",
    },
    "configuration name": {
        "description": "The name of the configuration evaluated",
        "dimensionality": "scalar",
        "type": "string",
    },
    "model chemistry": {
        "description": "The model chemistry (level spec) used",
        "dimensionality": "scalar",
        "type": "string",
    },
    "elapsed time": {
        "description": "Wall-clock time for this evaluation",
        "dimensionality": "scalar",
        "type": "float",
        "units": "s",
        "format": ".3f",
    },
}
