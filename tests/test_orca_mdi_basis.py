# -*- coding: utf-8 -*-

"""Regression: the Energy step's MDI engine runs the basis the user chose.

The Model Chemistry match used to keep the advertised offering's
``mdi_basis_arg`` (def2-SVP), so ORCA over MDI ran def2-SVP whatever basis was
chosen. This runs the real chain -- match, the Energy step's method/basis rule,
ORCA's engine command, the MDI engine, ORCA -- and checks the generated input
and the energy. Skipped where ORCA, pymdi or the plug-ins are missing.
"""

import shutil
import subprocess

import numpy as np
import pytest

from energy_step.energy import Energy

mdi = pytest.importorskip("mdi")
mc_module = pytest.importorskip("model_chemistry_step.model_chemistry")
orca_step = pytest.importorskip("orca_step")
seamm_mdi = pytest.importorskip("seamm_mdi")

WATER = np.array([[0.0, 0.0, 0.117], [0.0, 0.757, -0.469], [0.0, -0.757, -0.469]])


def _orca():
    from seamm_exec import Local

    try:
        config = orca_step.ORCAStep.get_executor_config(Local(), {"root": "~/SEAMM"})
    except Exception:
        return None
    code = config.get("code")
    return code if code and shutil.which(code) else None


@pytest.mark.parametrize("basis", ["def2-TZVP", "bse:def2-TZVP"])
def test_energy_step_mdi_runs_the_chosen_basis(basis, tmp_path):
    orca = _orca()
    if orca is None:
        pytest.skip("ORCA is not configured")
    from seamm_exec import Local

    available = mc_module.discover_model_chemistries()
    mc = mc_module.match_model_chemistry(f"ORCA:DFT@B3LYP/{basis}", available)
    method, mdi_basis = Energy._mdi_method_and_basis(mc, mc["options"])
    assert mdi_basis == basis

    scratch = tmp_path / "engine"

    def build_argv(hostname, port):
        return orca_step.ORCAStep.get_mdi_engine_command(
            Local(),
            {"root": "~/SEAMM"},
            method=method,
            basis=mdi_basis,
            port=port,
            hostname=hostname,
            n_atoms=3,
            extra_args=["--scratch", str(scratch)],
        )

    with seamm_mdi.MDIEngine(build_argv, [8, 1, 1]) as engine:
        engine.set_coordinates(WATER, units="Å")
        energy = engine.energy(units="hartree")

    first = (scratch / "orca.inp").read_text().splitlines()[0]
    if basis.startswith("bse:"):
        assert first == "! B3LYP AutoAux EnGrad"
        assert (scratch / "basis.bas").exists()
    else:
        assert first == "! B3LYP AutoAux def2-TZVP EnGrad"

    # The same energy as ORCA run directly with def2-TZVP
    direct = tmp_path / "direct"
    direct.mkdir()
    (direct / "orca.inp").write_text(
        "! B3LYP AutoAux def2-TZVP EnGrad\n* xyz 0 1\n"
        + "".join(f"{el} {x} {y} {z}\n" for el, (x, y, z) in zip("OHH", WATER.tolist()))
        + "*\n"
    )
    out = subprocess.run(
        [orca, "orca.inp"], cwd=direct, capture_output=True, text=True
    ).stdout
    reference = float(
        [line for line in out.splitlines() if "FINAL SINGLE POINT ENERGY" in line][
            -1
        ].split()[-1]
    )
    assert energy == pytest.approx(reference, abs=1e-8)
