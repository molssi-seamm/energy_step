=======
History
=======

2026.9.19 (2026-09-19)
----------------------

* Structure selection now uses SEAMM's standard block (systems and configurations,
  by name or from a variable), so the Energy step can e.g. evaluate all
  configurations of every system, or the systems matching a pattern.
* The output states exactly what was stored on each configuration (energy,
  gradients, stress) and mentions forces only when they were calculated; the CSV
  summary is secondary.
* Requires seamm 2026.9.18.1 or later.


2026.9.18 (2026-09-18)
----------------------

* Initial release. Evaluates the energy, gradients and (periodic) stress of one or
  many configurations with the upstream Model Chemistry driven as a resident MDI
  engine; results stored per configuration and on the atoms, with ``energies.csv``
  and table/variable output. Validated with an xnn MACE model (1000 water
  configurations in 14 s) and with MOPAC PM6-ORG.
* Plug-in created using the SEAMM plug-in cookiecutter.
