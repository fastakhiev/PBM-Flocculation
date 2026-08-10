# Third-Party Notices

Python and npm dependencies are listed with pinned versions in
`backend/requirements.txt` and `pbm_model_interface/package-lock.json`. Each is
distributed under its own license. A release reviewer must verify that the
grant's distribution terms are compatible with those licenses.

Machine-readable CycloneDX development inventories are supplied in
`docs/sbom-python.cdx.json` and `docs/sbom-npm.cdx.json`. The Windows build
script generates platform-specific inventories in the release folder. These
files identify components but do not replace review of their license terms.

## Brian Moore MATLAB Eigenvalue Routine

`matlab_code/eigenFrancis.m` states that it is based on work by Brian Moore:

Copyright (c) 2014, Brian Moore. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
* Neither the name of the copyright holder nor the names of its contributors
  may be used to endorse or promote products derived from this software without
  specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## John Burkardt Jacobi Routine

`matlab_code/eigenJacobi.m` states that it is based on John Burkardt's work and
distributed under GNU LGPL 3.0. The LGPL license text is available at
https://www.gnu.org/licenses/lgpl-3.0.txt and must accompany a distribution that
includes this file or a derivative governed by that license.

## Supplied EQMOM MATLAB Sources

Authorship and redistribution permission for `computeLogNormalNew.m`,
`computeGaussWigert.m`, and the remaining supplied MATLAB sources are not stated
in their headers. Written provenance and permission from the relevant rights
holders are required before external distribution. They are reference sources
and are not packaged into the Python executable.
