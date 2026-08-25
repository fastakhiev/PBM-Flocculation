# Data Provenance

## Included Test Data

The development workspace currently contains unapproved derived CSV files for
BHMW 14 mg/g, E1 8 mg/g, and E1++++ 10 mg/g, plus initial-moment files. They
were transcribed from `PCC_test.docx` and supplied MATLAB material. These files
and source documents are intentionally excluded by `.gitignore` until the data
owner approves their distribution.

Before external distribution, the responsible investigator must document for
each file:

| Field | Required value |
| --- | --- |
| Original owner | Person or institution |
| Original source | Lab file, publication table, or instrument export |
| Collection date and method | Experimental provenance |
| Units | Time, d43, DF, and every moment |
| Transformations | Digitization, rounding, normalization, corrections |
| Distribution permission | Written authorization and restrictions |
| Approved checksum | SHA-256 of the distributed file |

`PCC_test.docx`, article images, and PDFs are source documents, not runtime
assets. They must not be included in a release unless redistribution rights are
confirmed.

For BHMW 14 mg/g, `PCC_test.docx` contains `M1 = 0.679`. On 2026-08-12 the
data owner directly corrected the value used for the MATLAB result to
`M1 = 0.57`. The local `PCC_test_BHMW_14mg_moments.csv` and MATLAB runner use
the corrected value; both source records must be retained with the project.

For E2 8 mg/g, the data owner directly confirmed on 2026-08-13 that the 17
experimental `d43` and `DF` values and moments `[1; 1.2187; 1.9071; 3.8319;
9.8864]` are correct, and corrected `DF_max` from `2.72` to `2.49`. The local
`PCC_test_E2_8mg_d43_DF.csv` uses the corrected value.

For E1 4 mg/g, the data owner clarified on 2026-08-13 that the experimental
series still begins with `DF_exp(1) = 1.65`, while the source Excel model input
was separately set to `DF0 = 1.79`; `DF_max = 2.39`. The CSV retains the
experimental `1.65` and records the separate model input as `dF 0;;1.79`.

Every optimization report records the SHA-256 hashes and original filenames of
the two uploaded CSV files. A report is only reproducible when those exact
inputs are retained under the grant's data-management policy.

The `PCC_test_N_*.csv` files were transcribed from `PCC_test_N.docx` received
on 2026-08-24. In the scientific runner, model `DF0` defaults to
`DF_exp(1)`. Therefore E1 6, E3 6, and E3 8 retain their second experimental
DF measurements (`1.58`, `1.60`, and `1.59`) but use model `DF0 = 1.65`.
E1 4 remains the documented exception with `DF0 = 1.79`. Its nearly
degenerate moments are retained verbatim. Because decimal rounding makes the
final canonical coordinate slightly negative, the numerical inversion uses
the one-node log-normal boundary that reconstructs all five supplied moments
with maximum relative log error below `2.4e-11`; the uploaded values themselves
are not changed.
