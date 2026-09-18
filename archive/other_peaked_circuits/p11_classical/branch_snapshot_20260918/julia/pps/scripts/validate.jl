using JSON
using PauliPropagation
using P11PPS

function validate_case(path)
    p = JSON.parsefile(path)
    n = Int(p["num_qubits"])
    q = Int(p["observable_qiskit_zero_based"]) + 1
    circuit = [P11PPS._gate(r) for r in p["gates"]]
    result = propagate(circuit, PauliString(n, :Z, q, 1.0); min_abs_coeff=0.0,
                       max_weight=Inf, heisenberg=true, thread=false)
    actual = overlapwithzero(result)
    expected = Float64(p["expected"])
    err = abs(actual - expected)
    name = String(p["name"])
    println("$name: actual=$(actual) expected=$(expected) error=$(err) terms=$(length(result))")
    err <= 1e-10 || error("validation failed for $name")
end

for path in ARGS
    p = JSON.parsefile(path)
    haskey(p, "name") && validate_case(path)
end
println("VALIDATION_PASS")
