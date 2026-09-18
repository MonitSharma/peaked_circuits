OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
u(0.21,-0.48,0.73) q[0];
cz q[0],q[1];
