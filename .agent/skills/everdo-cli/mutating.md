# Mutating items

See [data-model.md](data-model.md) for the ID-prefix mechanic — every `<ID>` below accepts a 4+ hex prefix.

## Create

```
everdo-cli item create "Buy milk"                              # action in inbox
everdo-cli item create "Buy milk" --note "2%" --list next      # in Next
everdo-cli item create "Project X" --type project --list next  # a project
everdo-cli item create "My notebook" --type notebook --list next
everdo-cli item create "note body" --type note --parent <NOTEBOOK_ID> --list next
everdo-cli item create "subtask" --parent <PROJECT_ID> --list next
everdo-cli item create "Pay rent" --tag finance --tag urgent   # with tags (must exist)
```

Prints the new item's id on stdout — capture it for follow-up commands (full item with `--json`).

## Change fields — `item set`

One verb sets any combination of fields on a single item (it maps to one whole-item update, so several flags in one call is the efficient way):

```
everdo-cli item set <ID> --title "new title"
everdo-cli item set <ID> --note  "new note body"
everdo-cli item set <ID> --due   1735680000        # unix seconds, or 'none' to clear
everdo-cli item set <ID> --list  next              # move to a list (friendly name or raw code)
everdo-cli item set <ID> --type  project           # convert type (action/project/note/notebook)
everdo-cli item set <ID> --parent <PROJECT_ID>     # attach to a project/notebook
everdo-cli item set <ID> --parent none             # detach
everdo-cli item set <ID> --title "X" --list next --due none   # several fields at once
```

`--parent` follows the inbox→Next auto-promote rule — see [projects-notebooks.md](projects-notebooks.md).

`item set` is single-id (the values are per-item). The lifecycle verbs below are batch.

## Batch lifecycle verbs

Take 1..N ids:

```
everdo-cli item complete   <ID> [<ID>...]        # mark done
everdo-cli item uncomplete <ID> [<ID>...]
everdo-cli item focus      <ID> [<ID>...]        # star
everdo-cli item unfocus    <ID> [<ID>...]
everdo-cli item trash      <ID> [<ID>...]        # soft delete (to Trash; reversible)
everdo-cli item delete     <ID> [<ID>...] --permanent  # hard delete + tombstone (irreversible)
```

## Tags on an item

Tags are referenced by **title** and must already exist in the catalogue (`tag list`); an unknown title is an error. `add`/`remove` are additive/subtractive and never clobber tags you didn't name — prefer them. `set` replaces the whole list:

```
everdo-cli item tag add    <ID> finance urgent   # add one or more (idempotent)
everdo-cli item tag remove <ID> urgent           # remove one or more
everdo-cli item tag set    <ID> finance          # replace tags with exactly these
```

To strip a whole tag family in one pass, `item tag remove` takes a `--match` glob instead of an id+titles. Scope is the listed ids, or **all items** when none are given — and it is one `/sync` round-trip regardless of how many items are touched:

```
everdo-cli item tag remove --match '~suggest/*'            # from every item
everdo-cli item tag remove --match 'temp-*' <ID> [<ID>...] # only within these items
```

Filter by tag with `everdo-cli item list --tag finance` (matches inherited tags too).

## Fail-fast batch resolution

If any id in a batch is unresolvable (typo, ambiguous prefix), the command errors **before** doing any mutation, so the batch is never half-applied because of a bad id.
