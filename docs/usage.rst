=====
Usage
=====

The Energy step needs a *Model Chemistry* step before it in the flowchart: an
``xnn:MLFF@<model>`` machine-learned force field, ``MOPAC:SQM@PM6-ORG``,
``xTB:SQM@GFN2-xTB``, or an ORCA model such as ``ORCA:DFT@B3LYP/def2-TZVP``, for
example. It then evaluates that method's energy for the structures you select.

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

The step hands the structures to SEAMM's evaluator, which chooses how to compute them;
the numbers are the same either way.

Over MDI
    For programs with a fast, resident engine -- MLFFs, MOPAC, xTB -- the structures are
    grouped by what an MDI engine keeps fixed for a session (the atomic numbers in order,
    charge, spin multiplicity and periodicity), one engine is started per group, and the
    structures are sent one after another (``>CELL`` for periodic systems, then
    ``>COORDS``), reading back ``<ENERGY``, ``<FORCES`` and ``<STRESS``. The program's
    start-up (and, for an MLFF, loading the model) is paid once.

As separate calculations
    For ORCA, which runs once per structure anyway, and for any program that can run this
    way (ORCA, MOPAC) when the job's tasks go to a cluster queue, each structure is a
    separate calculation. MLFFs and xTB always use their MDI engine. They run
    concurrently on this machine or are bundled into batch jobs on the cluster, and are
    kept in ``tasks/c<id>/`` in the step's directory. Running the job again in the same
    directory reuses the finished calculations.

A structure that a program cannot run as a separate calculation (a periodic system for
ORCA or MOPAC) goes to its MDI engine even when the others run as separate calculations,
and the output then says how many went each way. If there is no engine on this machine
(a cluster queue, with the program installed only there), that structure fails with the
reason and the others are stored.

The per-structure energies, forces and timings are written to ``energies.csv`` in the
step's directory; up to 25 structures are also tabled in the step output. If some
structures fail, the others are still stored and the step then stops, listing the
failures.

Notes
-----

* A flowchart edited by hand may name a Model Chemistry that can be evaluated neither
  over MDI nor as separate calculations; the step then stops with a message naming it
  rather than silently doing nothing.
* The Model Chemistry used here need not be the one used to build the structures: a
  cheap method can generate an ensemble and an expensive one label it, or vice versa.
