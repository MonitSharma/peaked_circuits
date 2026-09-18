# Interpretation and claim boundaries

The defensible claims are layered:

1. **Hardware execution:** P11 and P12 completed on Quantinuum Helios-1 with
   the retained provider costs, timings, and raw outputs.
2. **Hardware recovery:** offline decoders extracted candidate strings from the
   returned samples, with P12 showing agreement among three robust observed-data
   methods.
3. **External verification:** later known-answer/score information is recorded
   separately and is not fed back into target-blind decoding.
4. **Quantum advantage:** not established by these runs alone.

In particular, recovering a hidden string on quantum hardware does not prove
that the hardware outperformed classical computation. That claim requires a
pre-specified classical baseline, comparable resources and costs, uncertainty
accounting, and the tracker’s accepted verification/evaluation procedure.

The classical research history remains on `p11_classical` and is not copied or
rewritten here. During a future integration, it should be linked as a separate
baseline record rather than merged into the hardware result narrative.
