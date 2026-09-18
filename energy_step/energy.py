# -*- coding: utf-8 -*-

"""Non-graphical part of the Energy step in a SEAMM flowchart.

The Energy step evaluates the energy, and optionally the gradients (forces) and
stress, of one or many structures using the Model Chemistry published upstream
(the ``_model_chemistry`` workspace variable), driving the program as a resident
MDI engine via ``seamm_mdi``. The engine is started once per distinct topology
(elements, charge, multiplicity, periodicity) and then fed the structures one
after another over the warm connection, so labelling hundreds of structures --
e.g. with a machine-learned force field -- costs a single engine start-up.

Results are stored per configuration: the energy, gradients and stress as
properties, and the gradients also on the atoms (so downstream writers such as
the extended-XYZ format emit them as forces).
"""

import csv
import logging
from pathlib import Path
import pprint  # noqa: F401
import time

import numpy as np

import energy_step
import seamm
from seamm_util import ureg, Q_  # noqa: F401
import seamm_util.printing as printing
from seamm_util.printing import FormattedText as __

# In addition to the normal logger, two logger-like printing facilities are
# defined: "job" and "printer". "job" send output to the main job.out file for
# the job, and should be used very sparingly, typically to echo what this step
# will do in the initial summary of the job.
#
# "printer" sends output to the file "step.out" in this steps working
# directory, and is used for all normal output from this step.

logger = logging.getLogger(__name__)
job = printing.getPrinter()
printer = printing.getPrinter("Energy")

# Units used for the stored results.
_E_UNITS = "kJ/mol"
_G_UNITS = "kJ/mol/Å"
_S_UNITS = "GPa"

# Print a per-structure table only up to this many structures; beyond that the
# table goes to energies.csv in the step directory and the output has a summary.
_MAX_TABLE_ROWS = 25


class Energy(seamm.Node):
    """
    The non-graphical part of an Energy step in a flowchart.

    Attributes
    ----------
    parser : configargparse.ArgParser
        The parser object.

    options : tuple
        It contains a two item tuple containing the populated namespace and the
        list of remaining argument strings.

    parameters : EnergyParameters
        The control parameters for Energy.

    See Also
    --------
    TkEnergy,
    Energy, EnergyParameters
    """

    def __init__(self, flowchart=None, title="Energy", extension=None, logger=logger):
        """A step for Energy in a SEAMM flowchart.

        Parameters
        ----------
        flowchart: seamm.Flowchart
            The non-graphical flowchart that contains this step.

        title: str
            The name displayed in the flowchart.
        extension: None
            Not yet implemented
        logger : Logger = logger
            The logger to use and pass to parent classes

        Returns
        -------
        None
        """
        logger.debug(f"Creating Energy {self}")

        super().__init__(
            flowchart=flowchart,
            title="Energy",
            extension=extension,
            module=__name__,
            logger=logger,
        )  # yapf: disable

        self._metadata = energy_step.metadata
        self.parameters = energy_step.EnergyParameters()

    @property
    def version(self):
        """The semantic version of this module."""
        return energy_step.__version__

    @property
    def git_revision(self):
        """The git version of this module."""
        return energy_step.__git_revision__

    def description_text(self, P=None):
        """Create the text description of what this step will do.

        Parameters
        ----------
        P: dict
            An optional dictionary of the current values of the control
            parameters.
        Returns
        -------
        str
            A description of the current step.
        """
        if not P:
            P = self.parameters.values_to_dict()

        what = "the energy"
        if self._truthy(P["gradients"]):
            what += " and gradients"
        if self._truthy(P["stress"]):
            what += ", plus the stress for periodic systems,"

        which = seamm.standard_parameters.structure_selection_description(P)
        # "The current configuration ... will be used." -> "... of the current ..."
        which = which[0].lower() + which[1:]
        if which.endswith(" will be used."):
            which = which[: -len(" will be used.")]

        if self._truthy(P["gradients"]):
            stored = (
                "The energy and gradients will be stored on each configuration as "
                "properties, and the gradients also on the atoms, so a following "
                "Write Structure step can write them out, e.g. as an extended XYZ "
                "file with REF_energy and REF_forces."
            )
        else:
            stored = (
                "The energy will be stored on each configuration as a property, so "
                "a following Write Structure step can write it out."
            )
        text = (
            f"Calculate {what} of {which}, using the model chemistry defined "
            f"earlier in the flowchart driven as a resident MDI engine. {stored}"
        )

        return self.header + "\n" + __(text, indent=4 * " ").__str__()

    # ------------------------------------------------------------------ #
    # Running
    # ------------------------------------------------------------------ #

    def run(self):
        """Run an Energy step.

        Returns
        -------
        seamm.Node
            The next node object in the flowchart.
        """
        next_node = super().run(printer)
        P = self.parameters.current_values_to_dict(
            context=seamm.flowchart_variables._data
        )

        printer.important(__(self.description_text(P), indent=self.indent))
        printer.important("")

        directory = Path(self.directory)
        directory.mkdir(parents=True, exist_ok=True)

        mc = self._model_chemistry()
        self.model = mc["level"]
        # Say which model file is used when the provider reports one (an MLFF
        # checkpoint may come from a personal or a machine-wide directory).
        source = mc.get("options", {}).get("source")
        if source:
            printer.important(
                __(f"Using the model {mc['level']} from {source}.", indent=4 * " ")
            )
            printer.important("")

        configurations = self.select_configurations(P)
        if len(configurations) == 0:
            raise ValueError("The Energy step found no configurations to evaluate.")

        want_gradients = self._truthy(P["gradients"])
        want_stress = self._truthy(P["stress"])

        # Group the configurations by what the engine needs fixed for a session:
        # atom count/elements, charge, multiplicity and periodicity. Each group
        # gets one warm engine; the order of the configurations is preserved
        # within a group.
        groups = {}
        for index, configuration in enumerate(configurations):
            key = self._topology_key(configuration)
            groups.setdefault(key, []).append((index, configuration))

        rows = []
        t_start = time.perf_counter()
        n_engines = 0
        for key, members in groups.items():
            n_engines += 1
            elements, charge, multiplicity, periodicity = key
            first = members[0][1]
            with self._open_engine(mc, first) as engine:
                periodic = periodicity != 0
                if periodic and not engine.supports(">CELL"):
                    raise ValueError(
                        f"The model chemistry '{mc['level']}' MDI engine does not "
                        "accept a periodic cell (>CELL), so it cannot evaluate "
                        "periodic structures."
                    )
                do_stress = periodic and want_stress and engine.supports("<STRESS")
                for index, configuration in members:
                    t0 = time.perf_counter()
                    data = self._evaluate(
                        engine, configuration, want_gradients, do_stress, periodic
                    )
                    data["elapsed time"] = time.perf_counter() - t0
                    data["configuration name"] = configuration.name
                    data["model chemistry"] = mc["level"]

                    self._store(configuration, data, want_gradients, do_stress)
                    rows.append((index, configuration, data))

        elapsed = time.perf_counter() - t_start
        rows.sort(key=lambda r: r[0])

        # Cite MDI, which makes the resident-engine evaluation possible. The
        # plug-in's own reference is added by the base class.
        if "mdi" in self._bibliography:
            self.references.cite(
                raw=self._bibliography["mdi"],
                alias="mdi",
                module="energy_step",
                level=1,
                note="The MolSSI Driver Interface used to drive the engine.",
            )

        self.analyze(
            P=P,
            rows=rows,
            model_chemistry=mc["level"],
            n_engines=n_engines,
            elapsed=elapsed,
            directory=directory,
        )

        return next_node

    def _evaluate(self, engine, configuration, want_gradients, do_stress, periodic):
        """Evaluate one configuration on the warm engine; returns the data dict."""
        if periodic:
            engine.set_cell(configuration.cell.vectors(as_array=True), units="Å")
        xyz = configuration.atoms.get_coordinates(fractionals=False, as_array=True)
        engine.set_coordinates(np.asarray(xyz, dtype=float), units="Å")

        data = {"energy": float(engine.energy(units=_E_UNITS))}

        if want_gradients:
            forces = np.asarray(engine.forces(units=_G_UNITS), dtype=float)
            gradients = -forces
            data["gradients"] = gradients.tolist()
            data["maximum force"] = float(np.max(np.abs(forces)))
            data["rms force"] = float(np.sqrt(np.mean(forces**2)))

        if do_stress:
            data["stress"] = np.asarray(
                engine.stress(units=_S_UNITS), dtype=float
            ).tolist()

        return data

    def _store(self, configuration, data, want_gradients, do_stress):
        """Store the results on the configuration and via store_results.

        The energy, gradients and stress are always stored as properties (that is
        the purpose of the step); ``store_results`` additionally handles whatever
        the user asked to put in variables or tables.
        """
        self._put_property(configuration, "energy", data["energy"], _E_UNITS)
        if want_gradients:
            gradients = np.asarray(data["gradients"], dtype=float)
            configuration.atoms.set_gradients(gradients, fractionals=False)
            self._put_property(
                configuration, "gradients", data["gradients"], _G_UNITS, "json"
            )
        if do_stress:
            self._put_property(
                configuration, "stress", data["stress"], _S_UNITS, "json"
            )

        self.store_results(configuration=configuration, data=data)

    def _put_property(self, configuration, key, value, units, _type="float"):
        """Store a ``<key>#Energy#<model>`` property, defining it if needed."""
        name = self.metadata["results"][key]["property"].format(model=self.model)
        properties = configuration.properties
        if not properties.exists(name):
            description = self.metadata["results"][key]["description"]
            properties.add(
                name,
                _type,
                units=units,
                description=f"{description} ({self.model})",
                noerror=True,
            )
        properties.put(name, value)

    # ------------------------------------------------------------------ #
    # The MDI engine from the model chemistry
    # ------------------------------------------------------------------ #

    def _model_chemistry(self):
        """The ``_model_chemistry`` wrapper published upstream, checked for MDI."""
        if not self.variable_exists("_model_chemistry"):
            raise ValueError(
                "The Energy step needs a Model Chemistry: add a 'Model Chemistry' "
                "step before it to choose the method (e.g. an MLFF model, MOPAC "
                "PM6-ORG, or an ORCA DFT model) used for the energy."
            )
        mc = self.get_variable("_model_chemistry")
        options = mc.get("options", {}) if isinstance(mc, dict) else {}
        if not options.get("mdi_capable", False):
            raise ValueError(
                f"The model chemistry '{mc.get('level', mc)}' cannot be driven "
                "via MDI, which the Energy step requires. Choose an MDI-capable "
                "model chemistry (e.g. an xnn MLFF model, MOPAC, xTB or ORCA)."
            )
        return mc

    @staticmethod
    def _mdi_method_and_basis(mc, options):
        """The (method, basis) to launch the MDI engine with.

        ``method`` is the engine's real keyword -- ``options['mdi_method_arg']``
        when the program provides one -- falling back to the parsed
        ``mc['method']``. ``basis`` is ``options['mdi_basis_arg']``, or the
        user's basis from the level spec, or ``None`` for engines that take a
        method alone (MOPAC, xTB, an MLFF) and whose ``get_mdi_engine_command``
        has no basis argument.
        """
        method = options.get("mdi_method_arg") or mc.get("method")
        basis = options.get("mdi_basis_arg") or mc.get("basis")
        return method, basis

    def _open_engine(self, mc, configuration):
        """Start the MDI engine for ``configuration``'s topology.

        Returns a started ``seamm_mdi.MDIEngine`` (a context manager).
        """
        from seamm_mdi import MDIEngine

        options = mc.get("options", {})
        step = self.flowchart.plugin_manager.get(mc["step"])
        executor = self.flowchart.executor
        seamm_options = self.global_options
        method, basis = self._mdi_method_and_basis(mc, options)

        charge = configuration.charge
        multiplicity = configuration.spin_multiplicity
        n_atoms = configuration.n_atoms

        def build_argv(hostname, port):
            kwargs = {
                "method": method,
                "port": port,
                "hostname": hostname,
                "charge": charge,
                "multiplicity": multiplicity,
                "n_atoms": n_atoms,
            }
            if basis is not None:
                kwargs["basis"] = basis
            return step.get_mdi_engine_command(executor, seamm_options, **kwargs)

        elements = list(configuration.atoms.atomic_numbers)
        engine = MDIEngine(
            build_argv, elements=elements, name="Energy", logger=self.logger
        )
        engine.start()
        return engine

    @staticmethod
    def _topology_key(configuration):
        """What must stay fixed for one MDI engine session."""
        return (
            tuple(int(z) for z in configuration.atoms.atomic_numbers),
            int(configuration.charge),
            int(configuration.spin_multiplicity),
            int(configuration.periodicity),
        )

    @staticmethod
    def _truthy(value):
        return value is True or (isinstance(value, str) and value.lower() == "yes")

    # ------------------------------------------------------------------ #
    # Output
    # ------------------------------------------------------------------ #

    def analyze(
        self,
        P=None,
        rows=None,
        model_chemistry="",
        n_engines=1,
        elapsed=0.0,
        directory=None,
        indent="",
        **kwargs,
    ):
        """Summarize the results to the step's output and energies.csv."""
        if not rows:
            return

        n = len(rows)
        energies = np.array([data["energy"] for _, _, data in rows])
        have_forces = all("maximum force" in data for _, _, data in rows)
        have_stress = any("stress" in data for _, _, data in rows)

        # Always write the full per-structure table to a CSV file.
        if directory is not None:
            path = Path(directory) / "energies.csv"
            with path.open("w", newline="") as fd:
                writer = csv.writer(fd)
                header = ["index", "configuration", f"energy ({_E_UNITS})"]
                if have_forces:
                    header += [
                        f"max force ({_G_UNITS})",
                        f"rms force ({_G_UNITS})",
                    ]
                header.append("time (s)")
                writer.writerow(header)
                for index, configuration, data in rows:
                    row = [index + 1, configuration.name, f"{data['energy']:.4f}"]
                    if have_forces:
                        row += [
                            f"{data['maximum force']:.4f}",
                            f"{data['rms force']:.4f}",
                        ]
                    row.append(f"{data['elapsed time']:.3f}")
                    writer.writerow(row)

        stored = [f"the energy as the property 'energy#Energy#{self.model}'"]
        if have_forces:
            stored.append(
                "the gradients on the atoms and as the property "
                f"'gradients#Energy#{self.model}'"
            )
        if have_stress:
            stored.append(f"the stress as the property 'stress#Energy#{self.model}'")
        if len(stored) == 1:
            stored_text = stored[0]
        else:
            stored_text = ", ".join(stored[:-1]) + " and " + stored[-1]

        if n == 1:
            _, configuration, data = rows[0]
            text = (
                f"The {model_chemistry} energy of '{configuration.name}' is "
                f"{data['energy']:.4f} {_E_UNITS}."
            )
            if have_forces:
                text += (
                    f" The largest force component is {data['maximum force']:.4f} "
                    f"{_G_UNITS} (RMS {data['rms force']:.4f})."
                )
            printer.important(__(text, indent=4 * " "))
        else:
            text = (
                f"Evaluated {n} structures with {model_chemistry} in {elapsed:.2f} s "
                f"({1000 * elapsed / n:.1f} ms per structure) using {n_engines} "
                + ("engine session" if n_engines == 1 else "engine sessions")
                + "."
            )
            printer.important(__(text, indent=4 * " "))
            text = (
                f"The energies range from {energies.min():.4f} to "
                f"{energies.max():.4f} {_E_UNITS} (mean {energies.mean():.4f}, "
                f"standard deviation {energies.std():.4f})."
            )
            printer.important(__(text, indent=4 * " "))
            if have_forces:
                fmax = max(data["maximum force"] for _, _, data in rows)
                text = f"The largest force component is {fmax:.4f} {_G_UNITS}."
                printer.important(__(text, indent=4 * " "))

            if n <= _MAX_TABLE_ROWS:
                printer.important("")
                header = f"    {'#':>4s} {'Configuration':<30s} {'Energy':>14s}"
                if have_forces:
                    header += f" {'Max force':>12s}"
                printer.important(header)
                for index, configuration, data in rows:
                    line = (
                        f"    {index + 1:>4d} {configuration.name[:30]:<30s} "
                        f"{data['energy']:>14.4f}"
                    )
                    if have_forces:
                        line += f" {data['maximum force']:>12.4f}"
                    printer.important(line)
                units = f"    {'':>4s} {'':<30s} {_E_UNITS:>14s}"
                if have_forces:
                    units += f" {_G_UNITS:>12s}"
                printer.important(units)
                printer.important("")

        text = (
            f"Stored on each configuration: {stored_text}. A Write Structure step "
            "can write these out, e.g. as extended XYZ with REF_energy"
            + (" and REF_forces." if have_forces else ".")
        )
        printer.important(__(text, indent=4 * " "))
        if n > 1:
            printer.important(
                __(
                    "A per-structure summary (energy"
                    + (", maximum and RMS force" if have_forces else "")
                    + ", time) is in energies.csv in this step's directory.",
                    indent=4 * " ",
                )
            )
