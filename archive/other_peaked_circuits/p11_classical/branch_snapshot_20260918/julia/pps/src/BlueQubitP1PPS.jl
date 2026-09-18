module BlueQubitP1PPS

using JSON
using PauliPropagation

export load_stream, run_observable, bit_from_expectation

"""P1 adapter: Qiskit U(theta,phi,lambda)=Rz(phi)Ry(theta)Rz(lambda)."""
function _gate_records(record)
    name = Symbol(record["gate_name"])
    q = Int.(record["qargs_julia_one_based"])
    p = record["parameters"]
    if name == :u
        length(p) == 3 || error("P1 U gate requires three parameters")
        # Global phase is irrelevant to Z expectations. PauliPropagation's
        # rotations use exp(-i theta P/2), matching Qiskit Rz/Ry.
        return [PauliRotation(:Z, q[1], Float64(p[3])),
                PauliRotation(:Y, q[1], Float64(p[1])),
                PauliRotation(:Z, q[1], Float64(p[2]))]
    elseif name == :cz
        return [CliffordGate(:CZ, q)]
    else
        error("Unsupported P1 gate: $(record["gate_name"])")
    end
end

function load_stream(path::AbstractString)
    payload = JSON.parsefile(path)
    n = Int(payload["num_qubits"])
    circuit = Any[]
    for record in payload["gates"]
        append!(circuit, _gate_records(record))
    end
    return n, circuit, payload
end

observable(n::Integer, q::Integer) = PauliString(Int(n), :Z, Int(q), 1.0)
bit_from_expectation(value::Real) = abs(value) <= 1e-12 ? nothing : (value < 0 ? 1 : 0)

function run_observable(stream_path::AbstractString, q::Integer; min_abs_coeff=1e-3, threadsafe=true)
    n, circuit, payload = load_stream(stream_path)
    1 <= q <= n || error("observable index out of range")
    started = time()
    result = propagate(circuit, observable(n, q); min_abs_coeff=min_abs_coeff,
                       max_weight=Inf, heisenberg=true, thread=threadsafe)
    value = overlapwithzero(result)
    return Dict(
        "stream" => stream_path,
        "qasm_sha256" => payload["qasm_sha256"],
        "num_qubits" => n,
        "observable_q_julia_one_based" => q,
        "min_abs_coeff" => min_abs_coeff,
        "expectation" => value,
        "inferred_bit" => bit_from_expectation(value),
        "sign" => value > 0 ? 1 : value < 0 ? -1 : 0,
        "unresolved" => abs(value) <= 1e-12,
        "terms" => length(result),
        "elapsed_seconds" => time() - started,
        "julia_threads" => Threads.nthreads(),
    )
end

end
