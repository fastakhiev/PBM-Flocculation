# Security

The desktop server binds only to `127.0.0.1`. It has no remote authentication
and must not be exposed on a LAN or public interface.

Report security issues privately to the project owner. Do not include real
credentials, personal data, proprietary source documents, local SQLite files,
or unapproved experimental datasets in an issue or commit.

Uploads are limited to 2 MB, must use a `.csv` extension and UTF-8 encoding,
and are validated before calculation. Local `.env` files are ignored by Git.

Grant releases should be generated from a clean tagged commit, scanned with the
organization's approved malware and dependency tools, and distributed with the
generated SHA-256 manifest.
