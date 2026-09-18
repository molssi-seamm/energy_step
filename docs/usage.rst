=====
Usage
=====

The Energy step needs a *Model Chemistry* step before it in the flowchart, choosing a
method that can be driven as an MDI engine: an ``xnn:MLFF@<model>`` machine-learned force
field, ``MOPAC:SQM@PM6-ORG``, ``xTB:SQM@GFN2-xTB``, or an ORCA DFT model, for example.
It then evaluates that method's energy for the structures you select.

A typical flowchart to label an ensemble for training a force field::

    Parameters -> Model Chemistry -> from SMILES -> Normal Mode Sampling
               -> Energy (configurations: all) -> Write Structure (Results.extxyz)

Options
-------

Structure
    ``current`` for the current system, the name of a system, or a variable (``$name``)
    holding a list of configurations.

using configurations
    ``current``, ``all``, ``first``, ``last``, or a selection by name (``name is``,
    ``name matches`` with a glob, ``name regexp``). ``all`` is the usual choice for an
    ensemble written by an earlier step.

Calculate the gradients (forces)
    Also request the forces. They are stored on the atoms of each configuration and as
    the ``gradients#Energy#<model>`` property.

Calculate the stress (periodic systems)
    For periodic structures, also request the stress tensor (``<STRESS`` over MDI);
    ignored for molecular systems.

Results
    The Results tab lets you save the energy, gradients, stress, maximum/RMS force,
    configuration name and timing to variables or a table; ``store_results`` is called
    once per structure, so a table gets one row per configuration.

How it runs
-----------

The configurations are grouped by what an MDI engine keeps fixed for a session -- the
atomic numbers (in order), charge, spin multiplicity and periodicity -- and one engine is
started per group with ``seamm_mdi.MDIEngine``. Within a group the structures are sent
one after another (``>CELL`` for periodic systems, then ``>COORDS``) and ``<ENERGY``,
``<FORCES`` and ``<STRESS`` are read back, so the program's start-up (and, for an MLFF,
loading the model) is paid once. The per-structure energies, forces and timings are
written to ``energies.csv`` in the step's directory; up to 25 structures are also tabled
in the step output.

Notes
-----

* A flowchart edited by hand may name a Model Chemistry that is not MDI-capable; the
  step then stops with a message naming the model chemistry rather than silently doing
  nothing.
* The Model Chemistry used here need not be the one used to build the structures: a
  cheap method can generate an ensemble and an expensive one label it, or vice versa.
