# infra

`clickhouse/init.sql` and `postgres/init.sql` are placeholders — the real DDL comes from
`docs/Final_Thesis_Phase2/03-schemas-and-contracts.md` §3-4 (Week 2 task, not yet transcribed here).

`redpanda/` is only needed for the `full` Docker Compose profile (stream mode demo / Phase 3);
the `dev` profile used for experiments does not need it.
