using JSON
using P11PPS
using PauliPropagation

stream = ARGS[1]
prefix = parse(Int, ARGS[2])
threshold = parse(Float64, ARGS[3])
out = ARGS[4]
n, circuit, payload = load_stream(stream)
prefix = min(prefix, length(circuit))
started = time()
result = propagate(circuit[1:prefix], observable(n, 1); min_abs_coeff=threshold,
                   max_weight=Inf, heisenberg=true)
elapsed = time() - started
record = Dict(
    "stream" => stream, "qasm_sha256" => payload["qasm_sha256"],
    "prefix_gates" => prefix, "observable_q_julia_one_based" => 1,
    "min_abs_coeff" => threshold, "expectation" => overlapwithzero(result),
    "terms" => length(result), "elapsed_seconds" => elapsed,
    "gates_per_second" => prefix / elapsed, "julia_threads" => Threads.nthreads(),
    "blas_threads" => get(ENV, "OPENBLAS_NUM_THREADS", "unset"),
)
mkpath(dirname(out))
write(out, JSON.json(record, 2) * "\n")
println(JSON.json(record))
