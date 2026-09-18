# -*- coding: utf-8 -*-

"""
energy_step
A SEAMM plug-in for calculating the energy and forces for many structures, using MDI.
"""

# Bring up the classes so that they appear to be directly in
# the energy_step package.

from energy_step.energy import Energy  # noqa: F401, E501
from energy_step.energy_parameters import EnergyParameters  # noqa: F401, E501
from energy_step.energy_step import EnergyStep  # noqa: F401, E501
from energy_step.tk_energy import TkEnergy  # noqa: F401, E501

# Handle versioneer
from ._version import get_versions

__author__ = "Paul Saxe"
__email__ = "psaxe@molssi.org"
versions = get_versions()
__version__ = versions["version"]
__git_revision__ = versions["full-revisionid"]
del get_versions, versions
