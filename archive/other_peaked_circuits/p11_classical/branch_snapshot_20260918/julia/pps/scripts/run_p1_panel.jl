using JSON
include(joinpath(@__DIR__, "..", "src", "BlueQubitP1PPS.jl"))
using .BlueQubitP1PPS

stream = ARGS[1]
threshold = parse(Float64, ARGS[2])
outdir = ARGS[3]
qs = parse.(Int, ARGS[4:end])
mkpath(outdir)
for q in qs
    result = run_observable(stream, q; min_abs_coeff=threshold)
    path = joinpath(outdir, "q$(q)_t$(replace(string(threshold), "." => "p", "-" => "m")).json")
    write(path, JSON.json(result, 2) * "\n")
    println(JSON.json(result))
end
