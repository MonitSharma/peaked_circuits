# P8 correlation-aware graph decoder

The native graph state now has a sequential projection decoder in `src/p12_recovery/peak/native_graph_decoder.py`. It does not use product-majority marginals. At each logical qubit it branches on 0 and 1, projects the corresponding physical tensor, canonically regauges the child network, scores the child by its projected squared norm, and keeps the top `B` branches. The output bitstring is in original logical-qubit order.

The runner accepts repeated `--decode-beam` options, for example:

```text
--decode-beam 16 --decode-beam 32 --decode-beam 64
```

The two-qubit correlated control recovered the exact support structure at beam widths 1, 2, and 4. A P8 100-event χ=16 run with B=16/32/64 was started on the isolated HPC environment; its evolution completed, but projection plus full-network regauging was still running under the ten-minute bound. This establishes that the decoder is operational, while also identifying full-network branch copying/regauging as the immediate performance bottleneck.

No P8 candidate is certified by this decoder. Its branch probabilities describe the approximate BP-compressed graph state only.
