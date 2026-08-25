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

On 2026-08-25 protocol `EQMOM-PCC-2STAGE-1.6` was checked on macOS with the
`PCC_test_N` files, `G=312 s^-1`, and `d0=100 nm`:

- 29 backend tests and the TypeScript/Vite production build passed;
- the current Python CycloneDX inventory passed `pip-audit` with no known
  vulnerabilities, and both development SBOM files parsed successfully;
- `E3 8 mg/g`: two consecutive runs returned exactly the same
  `alpha_max=0.3491343`, `B=56.6803`, `gamma=0.3822215`, and
  `SSE=100.3636` in 100.24 s and 101.87 s; Table 2 reports `0.35`, `56`,
  `0.38`.
- `BHMW 14 mg/g`: `alpha_max=0.3216998`, `B=50.6671`,
  `gamma=0.2906654`, `SSE=99.7864`, 121.72 s; Table 2 reports `0.33`, `53`,
  `0.30`.

An expanded Halton screening found a lower `E3 8 mg/g` SSE at a remote
high-`B` basin. It is deliberately not part of protocol 1.6 because the goal
is reproduction of the supplied MATLAB local-start protocol, not an unsupported
claim of global identifiability. This sensitivity must be disclosed when
interpreting fitted parameters.

For `E1 4 mg/g`, the `PCC_test_N` input gives `M4/M3=1.8695901` while the
experimental initial `d43` is `2.73`. With the documented `G=312 s^-1` and
`d0=100 nm`, protocol 1.6 returns `alpha_max=1.0`, `B=61.7656`,
`gamma=0.5362910`, and `SSE=8349.1273`. The Table 2 point
`alpha_max=0.45`, `B=50` has `SSE=67896.6782` and predicts only
`d43=4.25...10.56` after time zero. This dataset/model combination therefore
cannot reproduce the published E1 4 result without a corrected input
normalization or a different model configuration.
