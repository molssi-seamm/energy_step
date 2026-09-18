# -*- coding: utf-8 -*-
"""
Control parameters for the Energy step in a SEAMM flowchart
"""

import logging
import seamm
import pprint  # noqa: F401

logger = logging.getLogger(__name__)


class EnergyParameters(seamm.Parameters):
    """
    The control parameters for the Energy step.

    The step evaluates the energy (and optionally the gradients and, for periodic
    systems, the stress) of one or many structures with the Model Chemistry
    published upstream, driving the program as a resident MDI engine so that
    hundreds of structures cost one engine start-up.

    See Also
    --------
    Energy, TkEnergy, EnergyParameters, EnergyStep
    """

    parameters = {
        # ------------------------------------------------------------------ #
        # Input: which structure(s) to evaluate -- SEAMM's standard block
        # (source systems / source configurations, by name or from a variable).
        # ------------------------------------------------------------------ #
        **seamm.standard_parameters.structure_selection_parameters,
        # ------------------------------------------------------------------ #
        # What to compute
        # ------------------------------------------------------------------ #
        "gradients": {
            "default": "yes",
            "kind": "boolean",
            "default_units": "",
            "enumeration": ("yes", "no"),
            "format_string": "",
            "description": "Calculate the gradients (forces):",
            "help_text": (
                "Whether to also calculate the gradients (forces) on the atoms. They "
                "are stored on the atoms of each configuration, so e.g. the Write "
                "Structure step's extended XYZ output carries them as REF_forces, "
                "and as the property gradients#Energy#<model>."
            ),
        },
        "stress": {
            "default": "yes",
            "kind": "boolean",
            "default_units": "",
            "enumeration": ("yes", "no"),
            "format_string": "",
            "description": "Calculate the stress (periodic systems):",
            "help_text": (
                "Whether to also calculate the stress tensor for periodic "
                "systems. Ignored for molecular systems."
            ),
        },
        # ------------------------------------------------------------------ #
        # Results
        # ------------------------------------------------------------------ #
        "results": {
            "default": {},
            "kind": "dictionary",
            "default_units": None,
            "enumeration": tuple(),
            "format_string": "",
            "description": "results",
            "help_text": "The results to save to variables or in tables.",
        },
    }

    def __init__(self, defaults={}, data=None):
        """
        Initialize the parameters, by default with the parameters defined above

        Parameters
        ----------
        defaults: dict
            A dictionary of parameters to initialize. The parameters
            above are used first and any given will override/add to them.
        data: dict
            A dictionary of keys and a subdictionary with value and units
            for updating the current, default values.

        Returns
        -------
        None
        """

        logger.debug("EnergyParameters.__init__")

        super().__init__(
            defaults={**EnergyParameters.parameters, **defaults}, data=data
        )
