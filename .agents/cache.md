# Cache & refresh

Reads are served from a local cache that auto-refreshes via incremental sync (5-second TTL within a single process). Mutations always pull a fresh view first. You normally don't need to think about it.

```
./everdo_cli.py refresh                 # bring cache up to date
./everdo_cli.py refresh --force         # bypass TTL (use after manual changes you know happened)
./everdo_cli.py changes                 # show the latest delta (diagnostic)
./everdo_cli.py backup /path/to/dump.json   # full snapshot to a file
```

## Drift recovery

If you suspect cache drift (items missing, edits not showing), `refresh --force` fixes it. If that still looks wrong, delete `everdo/.everdo_state.json` and run any command — a cold start re-pulls the full database.

---

For the state-file format and cache implementation details, see [memory-bank/architecture.md](memory-bank/architecture.md).
