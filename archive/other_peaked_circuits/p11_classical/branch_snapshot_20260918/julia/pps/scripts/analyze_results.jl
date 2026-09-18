using JSON

indir = ARGS[1]
out = ARGS[2]
records = Dict{String,Any}[]
for path in sort(filter(p -> endswith(p, ".json"), readdir(indir; join=true)))
    push!(records, JSON.parsefile(path))
end
best = isempty(records) ? nothing : records[argmin([r["elapsed_seconds"] for r in records])]
report = Dict("records" => records, "fastest" => best,
              "deterministic_expectation" => isempty(records) ? nothing : length(unique(round.(Float64[r["expectation"] for r in records], sigdigits=14))) == 1,
              "deterministic_terms" => isempty(records) ? nothing : length(unique(Int[r["terms"] for r in records])) == 1)
mkpath(dirname(out))
write(out, JSON.json(report, 2) * "\n")
println(JSON.json(report))
