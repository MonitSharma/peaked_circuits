OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
u(0.12,-0.31,0.77) q[0];
h q[1];
cz q[0],q[1];
u(0.9,0.2,-0.4) q[2];
cz q[1],q[2];

