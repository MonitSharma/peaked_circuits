using P11PPS
using JSON

stream = ARGS[1]
q = parse(Int, ARGS[2])
threshold = parse(Float64, ARGS[3])
out = length(ARGS) >= 4 ? ARGS[4] : "-"
result = run_observable(stream, q; min_abs_coeff=threshold)
text = JSON.json(result, 2) * "\n"
if out == "-"
    print(text)
else
    mkpath(dirname(out))
    write(out, text)
end
