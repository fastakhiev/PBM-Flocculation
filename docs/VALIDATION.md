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
- [ ] DEA and GA repeated runs produce identical results for the same seed.
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

The shortened optimizer settings used for smoke testing are not scientific
benchmarks and do not replace the Windows and MATLAB acceptance tests above.
