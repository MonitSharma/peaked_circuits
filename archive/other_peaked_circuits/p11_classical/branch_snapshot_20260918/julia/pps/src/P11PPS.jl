module P11PPS

using JSON
using PauliPropagation

export load_stream, observable, run_observable, bit_from_expectation

function _complex_matrix(raw)
    return ComplexF64[complex(Float64(cell[1]), Float64(cell[2])) for row in raw for cell in row]
end

function _matrix(raw)
    n = length(raw)
    return ComplexF64[complex(Float64(raw[i][j][1]), Float64(raw[i][j][2])) for i in 1:n, j in 1:n]
end

function _gate(record)
    name = Symbol(record["gate_name"])
    q = Int.(record["qargs_julia_one_based"])
    p = record["parameters"]
    if name == :rzz
        return PauliRotation([:Z, :Z], q, Float64(p[1]))
    elseif name == :rx
        return PauliRotation(:X, q[1], Float64(p[1]))
    elseif name == :ry
        return PauliRotation(:Y, q[1], Float64(p[1]))
    elseif name == :rz
        return PauliRotation(:Z, q[1], Float64(p[1]))
    elseif name == :h
        return CliffordGate(:H, q)
    elseif name == :x
        return CliffordGate(:X, q)
    elseif name == :y
        return CliffordGate(:Y, q)
    elseif name == :z
        return CliffordGate(:Z, q)
    elseif name == :s
        return CliffordGate(:S, q)
    elseif name == :sx
        return CliffordGate(:SX, q)
    elseif name == :cx
        return CliffordGate(:CNOT, q)
    elseif name == :cz
        return CliffordGate(:CZ, q)
    elseif name == :swap
        return CliffordGate(:SWAP, q)
    elseif name == :t
        return TGate(q[1])
    elseif haskey(record, "matrix_01_basis")
        return TransferMapGate(_matrix(record["matrix_01_basis"]), q)
    else
        error("Unsupported gate record: $(record)")
    end
end

function load_stream(path::AbstractString)
    payload = JSON.parsefile(path)
    n = Int(payload["num_qubits"])
    circuit = [_gate(record) for record in payload["gates"]]
    return n, circuit, payload
end

observable(n::Integer, q::Integer) = PauliString(Int(n), :Z, Int(q), 1.0)

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

bit_from_expectation(value::Real) = abs(value) <= 1e-12 ? nothing : (value < 0 ? 1 : 0)

end
