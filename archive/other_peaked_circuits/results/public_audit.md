# Public release audit

Passed: **True**

- [x] no_dot_env: No committed .env files
- [x] no_credential_files: No credential-like files
- [x] no_token_values: No token-like values
- [x] no_local_absolute_paths: No local home-directory paths
- [x] no_hidden_target: No 98-bit hidden target field
- [x] correct_repository_url: CITATION.cff repository URL
- [x] correct_author: Monit Sharma software authorship metadata
- [x] license_present: Apache-2.0 license present
- [x] reports_record_commit: ReportBase JSON artifacts record a Git commit
- [x] reports_have_hash_fields: ReportBase JSON artifacts include input hash provenance
- [x] no_raw_private_provider_metadata: Provider raw results are not part of a public release
- [x] generated_data_ignored: Provider/canonical/hardware generated data are ignored
- [x] no_local_nexus_auth_cache: No Nexus token, browser-login, or local authentication cache is in the repository
- [x] qir_artifacts_sanitized: QIR text and bitcode contain no local paths or credential-like values
- [x] nexus_reports_sanitized: Nexus syntax-check reports contain sanitized references and diagnostics
