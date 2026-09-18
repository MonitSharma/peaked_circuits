# P11 overnight state

The authoritative live state is
`results/p11_overnight/RUN_STATE.json`. The keep-awake supervisor is recorded
in `goal_sentinel.pid` and `caffeinate.pid`; `GOAL_COMPLETE` is reserved for
the final successful candidate or an exhaustive local no-go.
