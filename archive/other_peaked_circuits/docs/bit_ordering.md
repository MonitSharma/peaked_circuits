# Bit ordering

Canonical convention: a candidate has length 98; position `i` is logical `q[i]`, from `q[0]` on the
left to `q[97]` on the right. This differs from common SDK display order.

For one classical register `c[5]` displayed MSB-left, raw `00101` means `c[4]..c[0]`. With logical
`q[i] -> c[i]`, canonical order is therefore `10100` (`q[0]..q[4]`). This transformation is performed
only from an explicit mapping.

With registers `a=[c0,c1]` and `b=[c2,c3,c4]`, an MSB-left provider may display register `b` before
`a`, and reverse bits within each register. The exact layout is encoded as ordered
`classical_indices`; spaces are separators only. Missing, duplicate, or ambiguous entries raise errors.
Logical-to-physical routing and physical-to-classical measurement are composed into the machine-readable
`MeasurementMapping`; neither decimal qubit labels nor string positions are inferred lexically.

Milestone 2 records logical and compiled names, optional physical index, classical register/bit, raw
provider position, canonical position, mapping source, and confidence. Renamed or multiple registers
and scratch bits are allowed only with explicit provider ordering. Arrays are consumed in returned
order and are never silently reversed.
