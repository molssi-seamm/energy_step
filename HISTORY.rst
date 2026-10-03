=======
History
=======

2026.10.3 (2026-10-03)
----------------------

* The structures can now run as separate calculations as well as over an MDI engine;
  SEAMM chooses. ORCA runs them as separate calculations, several at a time, and with a
  job whose calculations go to a cluster queue, ORCA and MOPAC run them there. MLFFs,
  xTB and MOPAC on this machine keep the warm MDI engine. The numbers are the same
  either way.
* Separate calculations are kept in ``tasks/c<id>/``; rerunning the job reuses the
  finished ones.
* A structure the program cannot run as a separate calculation (a periodic system for
  ORCA or MOPAC) goes to its MDI engine, and the output says how many went each way.
  If some structures fail, the others are still stored and the step then stops, listing
  the failures.
* A configuration selected twice is evaluated once.
* The shared CI now runs on uv: ``devtools/conda-envs/test_env.yaml`` is removed, so
  ``requirements.txt`` is the one dependency list.
* Requires seamm-exec 2026.10.3 or later.


2026.9.19 (2026-09-19)
----------------------

* Structure selection now uses SEAMM's standard block (systems and configurations,
  by name or from a variable), so the Energy step can e.g. evaluate all
  configurations of every system, or the systems matching a pattern.
* The output states exactly what was stored on each configuration (energy,
  gradients, stress) and mentions forces only when they were calculated; the CSV
  summary is secondary.
* The output names the model file used when the provider reports one, e.g.
  ``personal:xnn/water.pt``, so a personal model shadowing a machine one is visible.
* Requires seamm 2026.9.18.1 or later.


2026.9.18 (2026-09-18)
----------------------

* Initial release. Evaluates the energy, gradients and (periodic) stress of one or
  many configurations with the upstream Model Chemistry driven as a resident MDI
  engine; results stored per configuration and on the atoms, with ``energies.csv``
  and table/variable output. Validated with an xnn MACE model (1000 water
  configurations in 14 s) and with MOPAC PM6-ORG.
* Plug-in created using the SEAMM plug-in cookiecutter.
