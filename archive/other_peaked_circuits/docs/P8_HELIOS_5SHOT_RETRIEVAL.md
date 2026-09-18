# P8 Helios-1 5-shot retrieval

The completed P8 hardware job returned a verifier-clean five-shot payload.

- Job: `dd2089ba-1e84-4b46-b104-f848e48e4bcc`
- Result: `609b7544-2bc0-4be0-8a55-cfc632e7082a`
- Target: `Helios-1`
- Requested/returned: **5/5 shots**
- Provider-reported cost: **30.3 HQC**
- Result schema: labeled QIR, 40 results per shot
- Raw payload SHA-256: `2a15aff559656085d2e4cb9db075ccde512f550c31b1170edb6bf6f5e4bed707`

The five logical-label-ordered outputs were all distinct. Pairwise Hamming
distances were 19, 20, 20, 20, 17, 25, 23, 28, 26, and 20; minimum 17,
maximum 28, mean 21.8. There is therefore no collision or tight cluster in
this five-shot sample.

The sample is too small to support candidate recovery. In particular, it does
not validate or refute the previously generated classical P8 candidate. The
raw QIR payload, reconstructed provider-order and logical-label-order shots,
counts, and metadata are preserved in
`results/hardware/p8_helios_5shot_20260829/`.
