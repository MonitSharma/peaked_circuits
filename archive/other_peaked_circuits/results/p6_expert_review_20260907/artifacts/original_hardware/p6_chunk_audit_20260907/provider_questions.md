# Draft for Quantinuum — not sent

We found a reproducible QIR result assembly issue in our installed qnexus SDK.
In `fetch_qsys_result_by_id`, the string-result branch appends `prev_str` (the
first frame before END) again for every subsequent chunk. This duplicates the
first shot, metadata, and header. Replaying that code exactly reproduces our
saved result payloads.

Affected P6 job IDs:
- 19c66922-84e0-4f78-99a7-5392f98a4143
- c9156c8f-a385-4467-b388-fc58127e93b8
- 95960cce-a39d-4650-a0d7-f262e3b0d0b3
- 0da697e8-de3a-4034-a0b2-1c9ff350c7b5

The chunk endpoint returns 100 complete frames for each job. Assembled SDK
downloads instead contain 103/104/104/103 frames. Parsing each chunk separately
gives 400 distinct 62-bit outputs, whereas the faulty assembly creates four
apparent repeated strings.

Please confirm that the original chunk outputs represent disjoint shots and
identify the SDK release fixing this assembly defect. Is an independent Nexus
UI export available with shot indices and execution timing? Can you provide
device-side calibration/fidelity diagnostics and compiled-circuit information
for these jobs? We have preserved chunk responses, input bitcode, hashes, and
the exact installed assembly source for reproduction.
