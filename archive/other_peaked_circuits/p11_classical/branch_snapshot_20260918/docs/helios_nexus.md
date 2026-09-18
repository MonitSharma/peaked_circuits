# Accessing Quantinuum Helios through Nexus

Helios is not an H1/H2-style `pytket-quantinuum` target. Current Quantinuum documentation places
Helios on the Nexus next-generation stack:

- discover account-visible targets with `qnexus.devices.get_all()`;
- configure Helios with `qnexus.models.HeliosConfig(system_name=...)`;
- use HUGR (normally produced by Guppy) or a supported QIR workflow for execution;
- use `QuantinuumConfig(device_name=...)` for H2, not for new Helios integrations.

Official references:

- [Quantinuum Systems access](https://docs.quantinuum.com/systems/user_guide/hardware_user_guide/access.html)
- [Quantinuum Systems workflow](https://docs.quantinuum.com/systems/user_guide/hardware_user_guide/workflow.html)
- [Nexus device API](https://docs.quantinuum.com/nexus/nexus_api/devices.html)
- [Nexus backend configurations](https://docs.quantinuum.com/nexus/nexus_api/backend_configs.html)
- [pytket to QIR](https://docs.quantinuum.com/nexus/trainings/notebooks/basics/qir/pytket_to_qir.html)

## Safe local access check

Install the complete quantum extra, authenticate in the browser, and then rerun discovery:

```bash
python -m pip install -e '.[quantum]'
qnx login
# Equivalent Python API: python -c "import qnexus as qnx; qnx.login()"
p12-recovery devices --refresh --only-p12-compatible
```

`qnx.login()` opens Quantinuum's browser authentication. Do not paste a password, access token, or
browser code into this repository, an issue, a terminal transcript committed to Git, or a Codex task.
Nexus stores its own local authentication tokens outside the repository.

The discovery command performs read-only API calls. It filters `get_all()` to the Quantinuum issuer,
records sanitized backend metadata, and labels a target accessible only when it was returned for the
authenticated Nexus account. It does not create a Nexus project or submit any job.

## Correct Helios configuration shape

The target name must come from authenticated discovery; do not guess it. The SDK configuration shape
is:

```python
import qnexus as qnx

config = qnx.models.HeliosConfig(
    system_name="<exact Helios system_name returned by discovery>",
    max_cost=10.0,  # required as an explicit spending ceiling for a future hardware job
)
```

An emulator configuration can additionally use
`qnexus.models.HeliosEmulatorConfig(n_qubits=...)`, but the exact emulator system name and available
capacity must still come from Nexus discovery. The application must not derive hardware, emulator,
or checker access from a name alone when provider metadata is available.

## Repository safety boundary

Milestone 2 installed and understood the Nexus client and discovered Helios correctly. Milestone 3
may upload validated QIR only to `Helios-1SC`, after a separate double authorization guard. It does
not:

- call `circuits.upload` or `hugr.upload`;
- upload QIR without strict local validation and explicit authorization;
- start a Nexus job for `Helios-1E`, `Helios-1`, H2, or an unknown target;
- run a Helios emulator in metrics mode;
- submit a hardware job;
- consume Nexus compilation quota or HQCs.

The P12 OpenQASM/pytket circuit is exported with `pytket-qir` to textual LLVM IR plus validated
bitcode. The syntax checker is configured with `HeliosConfig(system_name="Helios-1SC")`; the SDK
does not require `max_cost` for an `SC` target. A later emulator milestone must retrieve provider
register metadata and resolve provider output order. Treating Helios as a legacy
`QuantinuumBackend("Helios-1")` remains blocked.

## Current Helios-1E emulator shape

Current Nexus rejects a Helios emulator job without `emulator_config`. The deterministic 98-qubit
mapping programs use `HeliosEmulatorConfig(n_qubits=98)` with
`MatrixProductStateSimulator()` and `NoErrorModel()`. The execute call separately supplies
`n_qubits=[98]` and `max_cost=[...]`. MPS fits this zero-entanglement layout workload, while the ideal
error model prevents fidelity noise from obscuring the ordering experiment. This configuration does
not authorize physical `Helios-1`.

For the entangling P12 pilot, the MPS simulator is bounded with `backend="auto"`, `chi=128`, and
`zero_threshold=0.01`. The bound may truncate entanglement and therefore cannot support fidelity or
accuracy claims. It exists only to test the blinded provider-to-canonical pipeline.
