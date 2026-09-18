OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
u(0.3,0.2,-0.4) q[0];
cz q[0],q[1];
