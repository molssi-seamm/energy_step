====================
SEAMM Energy Plug-in
====================

.. image:: https://img.shields.io/github/issues-pr-raw/molssi-seamm/energy_step
   :target: https://github.com/molssi-seamm/energy_step/pulls
   :alt: GitHub pull requests

.. image:: https://github.com/molssi-seamm/energy_step/workflows/CI/badge.svg
   :target: https://github.com/molssi-seamm/energy_step/actions
   :alt: Build Status

.. image:: https://codecov.io/gh/molssi-seamm/energy_step/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/molssi-seamm/energy_step
   :alt: Code Coverage

.. image:: https://img.shields.io/lgtm/grade/python/g/molssi-seamm/energy_step.svg?logo=lgtm&logoWidth=18
   :target: https://lgtm.com/projects/g/molssi-seamm/energy_step/context:python
   :alt: Code Quality

.. image:: https://github.com/molssi-seamm/energy_step/workflows/Documentation/badge.svg
   :target: https://molssi-seamm.github.io/energy_step/index.html
   :alt: Documentation Status

.. image:: https://pyup.io/repos/github/molssi-seamm/energy_step/shield.svg
   :target: https://pyup.io/repos/github/molssi-seamm/energy_step/
   :alt: Updates for Dependencies

.. image:: https://img.shields.io/pypi/v/energy_step.svg
   :target: https://pypi.python.org/pypi/energy_step
   :alt: PyPi VERSION

A SEAMM plug-in for calculating the energy and forces of one or many structures with the
current Model Chemistry, driven as a resident MDI engine.

* Free software: BSD-3-Clause
* Documentation: https://molssi-seamm.github.io/energy_step/index.html
* Code: https://github.com/molssi-seamm/energy_step

Features
--------

* Evaluates the energy, gradients (forces) and, for periodic systems, the stress of
  the current configuration, every configuration of a system, or a selection by name.
* Uses whatever Model Chemistry precedes it in the flowchart -- a machine-learned force
  field from the `xnn plug-in`_, MOPAC, xTB, ORCA, ... -- provided it can be driven as
  an MDI engine.
* Starts the program once and feeds it the structures over the warm MDI connection, so
  labelling hundreds or thousands of structures (e.g. the ensembles from the Normal Mode
  Sampling, Dimer Builder or Extract Clusters steps) costs one start-up: ~14 ms per water
  molecule with an xnn MACE model on a laptop CPU.
* Stores the results on each configuration -- ``energy#Energy#<model>``,
  ``gradients#Energy#<model>``, ``stress#Energy#<model>`` -- and the gradients on the
  atoms, so the Write Structure step's extended XYZ output carries ``REF_energy`` and
  ``REF_forces`` for training.
* Writes ``energies.csv`` (energy, max/RMS force and timing per structure) in the step's
  directory and can save any result to variables or tables.

.. _xnn plug-in: https://molssi-seamm.github.io/xnn_step/index.html

Acknowledgements
----------------

This package was created with Cookiecutter_ and the
`molssi-seamm/cookiecutter-seamm-plugin`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`molssi-seamm/cookiecutter-seamm-plugin`: https://github.com/molssi-seamm/cookiecutter-seamm-plugin

Developed by the Molecular Sciences Software Institute (MolSSI_),
which receives funding from the `National Science Foundation`_ under
award ACI-1547580

.. _MolSSI: https://molssi.org
.. _`National Science Foundation`: https://www.nsf.gov
