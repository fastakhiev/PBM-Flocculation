# PBM Flocculation

Desktop research application for calibrating and simulating a two-node
log-normal Extended Quadrature Method of Moments (EQMOM) population balance
model for polymer-induced PCC flocculation.

The application performs a documented two-stage calibration:

1. `gamma` is fitted to all scattering-exponent (`DF`) measurements after
   time zero.
2. With `gamma` fixed, `alpha_max` and `B` are fitted to all `d43`
   measurements after time zero.

There are no material-specific parameter values, shear-rate substitutions,
or hidden fitting windows in the optimizer. Published Table 2 values are
displayed only as a labelled external reference and are not imported by the
optimization module.

## Scientific Status

Protocol version: `EQMOM-PCC-2STAGE-1.2`.

The Python implementation follows the supplied general PCC MATLAB code. It
has not yet been independently certified as numerically equivalent to the
authors' production MATLAB implementation. In particular, the normalization
and physical units of the supplied initial moments must be confirmed by the
data owner. The application reports a warning when initial `M4/M3` differs
from experimental `d43` by more than 5%.

Do not describe a calculated parameter as a reproduction of a published
value unless the input data, units, protocol version, and independent
MATLAB/Python benchmark are included with the result.

See:

- [Scientific method](docs/SCIENTIFIC_METHOD.md)
- [Validation record](docs/VALIDATION.md)
- [Data provenance](docs/DATA_PROVENANCE.md)
- [Citation](CITATION.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## Input Files

Experimental data must be UTF-8, semicolon-separated, contain two metadata
lines, at least five measurements, and one explicit `dF max` row:

```csv
;BHMW;
;14 mg/g;
Time(min);d43;DF
0;0.414;1.65
0.5;11.525;1.65
1.4;23.135;1.7925
2.3;26.589;1.8982
3.3;32.217;1.9764
dF max;;2.19
```

Time must start at zero and increase strictly. Decimal commas and decimal
points are accepted.

The model initial fractal dimension `DF0` is entered separately on the
optimization page. It is not inferred from the first experimental DF value.

Initial moments must contain exactly five positive values:

```csv
value
1
0.57
0.82
1.8
7
```

## Local Development

Prerequisites: Python 3.10.1 or newer, Node.js 20, and npm.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python cli.py api --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd pbm_model_interface
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Local overrides may be copied from
`backend/.env.example`; real `.env` files are intentionally excluded from
Git.

## Tests

```bash
cd backend
python -m unittest discover -s tests -v

cd ../pbm_model_interface
npm ci
npm run build
```

Pinned runtime and build dependencies are checked with `pip-audit`; the npm
production tree is checked with `npm audit --omit=dev --audit-level=high`.
Development CycloneDX snapshots are stored in `docs/`. The Windows build script
generates release-specific SBOM files from its own clean platform environment.

The reproducibility report downloaded from the Simulation page records input
SHA-256 hashes, software/protocol versions, seed, parameter bounds, optimizer
settings, complete fit metrics, trajectories, and diagnostics.

## Docker

The maintained container configuration uses SQLite and two services only:

```bash
docker compose up --build
```

Open `http://127.0.0.1:8080`. Database state is stored in the `pbm_data`
volume. PostgreSQL, Redis, and Celery are not required.

## Windows Release

Run from PowerShell on Windows with 64-bit CPython 3.12 (python.org or
Anaconda), Node.js 20, and npm installed:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

The release is written to `release\PBM-Flocculation`. It is intentionally a
one-directory package to avoid unpacking the scientific Python stack on every
startup. Launch `PBM-Flocculation.exe` and distribute the complete folder: the
adjacent `_internal` directory is required. The folder also contains the legal
notices, scientific method, validation record, citation, CycloneDX software
bills of materials, the `_ctypes` runtime DLL manifest, and recursive checksums.
When the selected Python belongs to Anaconda, the script creates and builds
from a clean Conda environment instead of layering a standard `venv` over the
Anaconda runtime.

## Submission Gate

Before external grant submission, the responsible investigator must sign off
on all items in [Validation](docs/VALIDATION.md), provide written permission
for the experimental data and supplied MATLAB sources, and confirm the grant
authority's licensing and data-retention terms. These are governance decisions
and cannot be established by the software itself.
