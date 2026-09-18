# P12 raw-result format note

The preserved file `raw_result.json` retains the original repository filename,
but its contents are the provider's textual framed result stream, beginning
with `HEADER`, `START`, and `METADATA` records. It is intentionally not
renamed: the original filename is part of the provenance record.

Use these artifacts as follows:

- `raw_result.json`: byte-preserved provider output with the original name;
- `raw_result_framing_repaired.qir`: byte-preserved output after the documented
  structural repair;
- `classical/raw/reconstructed_200_shots.jsonl`: normalized 200-shot data used
  by the deterministic recovery analysis;
- `classical/raw/reconstruction_manifest.json`: reconstruction algorithm and
  cycle-level hashes.

The package-level `SHA256SUMS` covers all of these files.
