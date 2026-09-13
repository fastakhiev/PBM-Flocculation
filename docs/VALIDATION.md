# Validation Record

## Automated Checks

The backend suite covers:

- DF/gamma behavior and reference trajectories;
- input schema and explicit `DF_max` validation;
- moment validation;
- fit statistics and degrees of freedom;
- cancellation during integration;
- the absence of material-specific shear rates and fitting windows.

The frontend gate is a clean TypeScript and Vite production build.

Run the checks exactly as documented in the root README and record the command,
date, operating system, Python/Node versions, commit SHA, and complete output in
the grant release record.

## Required Scientific Acceptance Tests

The following tests require investigator-owned MATLAB results and are not
automatically satisfiable from this repository:

- [ ] Verify the units and normalization of M0-M4 for every dataset.
- [ ] Compare Python and MATLAB DF trajectories at every measurement.
- [ ] Compare Python and MATLAB five-moment trajectories, not only `d43`.
- [ ] Compare objective values for a fixed grid of `alpha_max` and `B`.
- [ ] Re-run every reported case from clean processes on two computers.
- [ ] Report parameter sensitivity and uncertainty intervals.
- [ ] Explain discrepancies with the published Table 2 without changing the
      protocol after viewing target values.
- [ ] Obtain independent review and approval from the responsible investigator.

## Release Acceptance

- [ ] Backend tests pass from the clean 64-bit CPython 3.12 release environment.
- [ ] Frontend production build passes after `npm ci`.
- [ ] Python and npm dependency audits report no known high-severity issue.
- [ ] Release-specific CycloneDX SBOM files parse successfully.
- [ ] Packaged application embedded-server smoke test passes.
- [ ] Windows release starts on a clean Intel Core i3 test laptop.
- [ ] Python multi-start repeated runs produce identical results.
- [ ] Stop terminates active CPU work and a subsequent task can start.
- [ ] The downloaded JSON report reproduces the displayed result.
- [ ] Release SHA-256 values match `SHA256SUMS.txt`.
- [ ] No `.env`, local database, source document, or unapproved dataset is in
      the release.

Unchecked items must be disclosed as limitations in a submission. They must not
be represented as completed validation.

## Development Verification Log

On 2026-08-10 the following checks passed on macOS with Python 3.12:

- 17/17 backend unit and API integration tests;
- clean TypeScript/Vite production build;
- PyInstaller one-directory build and packaged embedded-server smoke test;
- packaged embedded server became ready in approximately 2.12 seconds;
- importing the API does not eagerly load NumPy, Pandas, SciPy, Matplotlib, or
  the GA package;
- short end-to-end DEA and GA calculations using `G=700`;
- two consecutive DEA runs returned identical parameter/error tuples;
- two consecutive GA runs returned identical parameter/error tuples;
- `pip-audit` reported no known vulnerabilities for
  `requirements-build.txt`;
- `npm audit --omit=dev` reported zero known vulnerabilities.

Those results belong to the superseded protocol 1.2. The shortened optimizer
settings used for that smoke test are not scientific benchmarks and do not
validate the current protocol or replace the Windows and MATLAB acceptance
tests above.

On 2026-08-26 protocol `EQMOM-PCC-2STAGE-1.7` was checked on macOS with the
`PCC_test_N` files, `G=312 s^-1`, and `d0=100 nm`:

- 31 backend tests and the TypeScript/Vite production build passed;
- the current Python CycloneDX inventory passed `pip-audit` with no known
  vulnerabilities, and both development SBOM files parsed successfully;
- `E3 8 mg/g`: `alpha_max=0.3491340`, `B=56.6807`,
  `gamma=0.3822215`, `SSE=100.3636`, 12.02 s; Table 2 reports `0.35`, `56`,
  `0.38`.
- `BHMW 14 mg/g`: `alpha_max=0.3216998`, `B=50.6671`,
  `gamma=0.2906654`, `SSE=99.7864`, 69.80 s; Table 2 reports `0.33`, `53`,
  `0.30`.

An expanded Halton screening found a lower `E3 8 mg/g` SSE at a remote
high-`B` basin. It is deliberately not part of protocol 1.7 because the goal
is reproduction of the supplied MATLAB local-start protocol, not an unsupported
claim of global identifiability. This sensitivity must be disclosed when
interpreting fitted parameters.

The corrected E1 files received on 2026-08-30 were checked separately with the
same protocol, `G=312 s^-1`, and `d0=100 nm`:

- `E1 4 mg/g`: `alpha_max=1.0`, `B=60.2234`, `gamma=0.5362910`,
  `SSE=7451.1369`, 10.79 s. The corrected moments still give
  `M4/M3=1.8858603`, while the experimental initial `d43` is `2.73`.
- `E1+ 12 mg/g`: `alpha_max=0.2971763`, `B=93.7236`,
  `gamma=0.1647059`, `SSE=1741.0143`, 10.03 s. Its moments give
  `M4/M3=2.7318230`, while the experimental initial `d43` is `0.351`.

Both initial-value discrepancies are retained as supplied and must be resolved
through source-data provenance or an explicitly documented model scale; the
optimizer does not silently rescale either dataset.

On 2026-08-31 protocol `EQMOM-PCC-2STAGE-1.8` was checked after adding the
explicit E1 4 moment `length_scale`, with `G=312 s^-1` and `d0=100 nm`:

- 32 backend tests passed;
- the E1 4 raw moments remained unchanged in the input and the recorded
  order-aware conversion produced model moments
  `[1, 2.7299916, 7.4528616, 20.3462913, 55.5453751]`;
- real multi-start optimization returned `alpha_max=0.6415636`, `B=52.4960`,
  `gamma=0.5362910`, `SSE=141.3226`, and `GOF=95.4724%` in 10.17 s;
- the modeled initial `d43` is exactly `2.73`, and no material-specific
  parameter, objective penalty, or published target value enters the fit.
