# Scientific Method

## Scope

The implemented model is a two-node log-normal EQMOM population balance model
with aggregation, fragmentation, and a time-dependent fractal dimension. The
scientific reference is the article listed in `CITATION.md`; the immediate
implementation reference is the supplied `matlab_code/fit_EQMOM_general_PCC.m`.

## Calibration Protocol

The protocol identifier is `EQMOM-PCC-2STAGE-1.5`.

1. Measurement time must start at zero. The initial point is excluded from
   fitting because the model initial condition is supplied independently.
2. `gamma` is estimated by bounded scalar minimization of DF residual SSE at
   every subsequent measurement. The model `DF0` is supplied explicitly in
   the experimental CSV `dF 0` metadata row and is independent from the first
   experimental DF value.
3. The estimated `gamma` is fixed.
4. Every start point from the supplied MATLAB runner is refined independently
   by bounded trust-region least squares using forward finite differences.
   Invalid trajectories are assigned the same directional finite residual as
   the runner. The solver is deterministic and implemented in SciPy; MATLAB is
   not required at runtime.
5. Selection is based on the lowest valid Stage 2 SSE. GOF is reported as a
   diagnostic and is not used as a stopping target or selection criterion.

Every optimizer setting is included in the per-run JSON report. No branch
depends on C-PAM name or dosage.

## Code Map

| Scientific operation | Python implementation | MATLAB reference |
| --- | --- | --- |
| DF evolution and gamma fit | `backend/app/pbm_model/eqmom.py` | `simulateDF`, `DFObjective` |
| Two-node log-normal inversion | `eqmom._two_node_lognormal` | `computeLogNormalNew.m` |
| Secondary Gauss-Wigert quadrature | `eqmom._gauss_wigert` | `computeGaussWigert.m` |
| Aggregation and breakup sources | `eqmom._moment_derivative` | `momentDerivative` in `fit_EQMOM_general_PCC.m` |
| Stage 2 objective and deterministic multi-start | `optimization._stage_two_functions`, `optimization._run_multistart_least_squares` | `trackedResidual`, `startPoints` |
| Fit diagnostics | `pbm_model/metrics.py` | `evaluateCandidate` |

## Inputs And Units

| Quantity | Application unit |
| --- | --- |
| Time | min in CSV; integrated in s |
| `d43` | unit used by the experiment |
| `G` | s^-1 |
| Primary diameter `d0` | nm in UI; converted to m inside the kernel |
| `gamma` | min^-1 |
| Model `DF0` | dimensionless; required `dF 0` metadata row in the experimental CSV |
| Initial moments | source normalization; `M4/M3` must match the experimental `d43` unit |

The current source data contain different apparent moment normalizations. The
software therefore does not silently rescale moments. It records the modeled
and experimental initial `d43` difference in the optimization audit. It also
records when measured DF values exceed the supplied limiting `DF_max`. Such a
diagnostic requires data-owner review before the run can support a scientific
claim.

## Numerical Method

The log-normal inversion ports the supplied four-slot Ridder search and Jacobi
eigensolver. The trajectory integrator uses the supplied MATLAB strategy: a
one-second outer step with step halving whenever a candidate moment state is
not positive and realizable. The minimum substep is `dt/1024` and at most 4096
attempts are allowed per outer step. Rejected halvings reuse `dM/dt` because
the state and parameters have not changed; accepted moments are numerically
identical to recomputing it. Cross-runtime equivalence still requires golden
MATLAB trajectories before publication-grade claims are made.

## Deliberate Exclusions

- Published Table 2 parameters never enter an optimization objective or a
  material-specific start point. The same supplied start set is used for every
  case.
- Experimental `G` is never replaced by another value.
- No plateau-only or material-specific fitting window is used.
- The application does not force parameters to agree with a paper.

These constraints prevent circular validation. A discrepancy from the article
is reported as a discrepancy to investigate, not corrected by hidden tuning.
The protocol targets reproducibility of the supplied local multi-start method;
it does not claim that the selected minimum is global outside those basins.
