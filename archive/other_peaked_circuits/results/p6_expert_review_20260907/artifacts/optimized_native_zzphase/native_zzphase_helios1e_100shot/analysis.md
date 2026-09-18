# P6 native-ZZPhase Helios-1E 100-shot approximate emulator analysis

- Job: `18423ac9-bf14-449c-a76a-130500be0b9d`
- Actual cost: **901.84 HQC**
- Configuration: MPS `chi=32`, `zero_threshold=0.05`, `NoErrorModel`
- Shots analyzed: **100**
- Unique bitstrings: **97**
- Frequency histogram: **96 strings occurred once; one string occurred four times**

The four-occurrence mode was:

`00111001000001001110101100010001101001100010010010011001100111`

Target-blind decoder summaries:

- Bitwise majority: `00110101000010101010101100010011100101100010000011010001110111`
- Weighted medoid: `00110101000010001010101100000011000101100010000011011101110111`
- Cluster consensus: `00110101000011001010101100010011000101100010000011011101110111`

This is an approximate, noiseless MPS emulator result. It is useful for pipeline and distribution diagnostics, but it is not hardware evidence and should not be used to replace the hardware candidate.
