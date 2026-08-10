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

Every optimization report records the SHA-256 hashes and original filenames of
the two uploaded CSV files. A report is only reproducible when those exact
inputs are retained under the grant's data-management policy.
