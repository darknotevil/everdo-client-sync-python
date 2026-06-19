# Cache & refresh

Reads are served from a local cache that auto-refreshes via incremental sync (5-second TTL within a single process). Mutations always pull a fresh view first. You normally don't need to think about it.

```
everdo-cli sync refresh                 # bring cache up to date
everdo-cli sync refresh --force         # bypass TTL (use after manual changes you know happened)
everdo-cli sync changes                 # show the latest delta (diagnostic)
everdo-cli sync status                  # server time, clock drift, last sync, cache size
everdo-cli sync backup /path/to/dump.json   # full snapshot to a file
```

## Drift recovery

If you suspect cache drift (items missing, edits not showing), `sync refresh --force` fixes it. If that still looks wrong, delete the state file and run any command — a cold start re-pulls the full database. The state file lives at `$XDG_CONFIG_HOME/everdo/state.json` (or `~/.config/everdo/state.json` by default); the portable per-checkout fallback is `<repo-root>/.config/everdo/state.json`.

---

For the state-file format and cache implementation details, see [../../memory-bank/architecture.md](../../memory-bank/architecture.md).
