using Test
using PauliPropagation
using P11PPS

@testset "P11 PPS adapter primitives" begin
    @test P11PPS.bit_from_expectation(0.2) == 0
    @test P11PPS.bit_from_expectation(-0.2) == 1
    @test P11PPS.observable(3, 2).nqubits == 3
end

@testset "gate conventions and overlap" begin
    @test P11PPS._gate(Dict("gate_name" => "h", "qargs_julia_one_based" => [2], "parameters" => Any[])) isa CliffordGate
    @test P11PPS._gate(Dict("gate_name" => "rzz", "qargs_julia_one_based" => [1, 3], "parameters" => Any[0.4])) isa FrozenGate
    generic = Dict("gate_name" => "u", "qargs_julia_one_based" => [1], "parameters" => Any[],
                   "matrix_01_basis" => Any[Any[Any[1.0, 0.0], Any[0.0, 0.0]], Any[Any[0.0, 0.0], Any[1.0, 0.0]]])
    @test P11PPS._gate(generic) isa TransferMapGate
    h = [CliffordGate(:H, 1)]
    @test overlapwithzero(propagate(h, PauliString(1, :Z, 1, 1.0); min_abs_coeff=0.0)) == 0.0
    @test overlapwithzero(propagate([], PauliString(3, :Z, 2, 1.0); min_abs_coeff=0.0)) == 1.0
end
