# Mutating items

See [data-model.md](data-model.md) for the ID-prefix mechanic — every `<ID>` below accepts a 4+ hex prefix.

## Create

```
./everdo_cli.py create "Buy milk"                              # action in inbox
./everdo_cli.py create "Buy milk" --note "2%" --list a         # in Next
./everdo_cli.py create "Project X" --type p --list a           # a project
./everdo_cli.py create "My notebook" --type l --list a         # a notebook
./everdo_cli.py create "note body" --type n --parent <NOTEBOOK_ID> --list a
./everdo_cli.py create "subtask" --parent <PROJECT_ID> --list a
```

Prints the new item's id on stdout — capture it for follow-up commands.

## Batch verbs (no target)

Take 1..N ids:

```
./everdo_cli.py complete   <ID> [<ID>...]        # mark done
./everdo_cli.py uncomplete <ID> [<ID>...]
./everdo_cli.py focus      <ID> [<ID>...]        # star
./everdo_cli.py unfocus    <ID> [<ID>...]
./everdo_cli.py trash      <ID> [<ID>...]        # soft delete (to Trash; reversible)
./everdo_cli.py delete     <ID> [<ID>...] --permanent  # hard delete + tombstone (irreversible)
```

## Batch verbs with target (`--to`)

```
./everdo_cli.py move    --to <list>       <ID> [<ID>...]   # list = inbox/next/waiting/scheduled/someday/archived/trash or raw code
./everdo_cli.py convert --to <type>       <ID> [<ID>...]   # type = a/p/n/l
./everdo_cli.py assign  --to <PROJECT_ID> <ID> [<ID>...]   # attach to project/notebook
./everdo_cli.py assign  --to none         <ID> [<ID>...]   # detach
```

## Single-id verbs

The second argument is per-item, so batching doesn't make sense:

```
./everdo_cli.py rename <ID> "new title"
./everdo_cli.py note   <ID> "new note body"
./everdo_cli.py due    <ID> 1735680000           # unix seconds, or 'none'
```

## Fail-fast batch resolution

If any id in a batch is unresolvable (typo, ambiguous prefix), the command errors **before** doing any mutation, so the batch is never half-applied because of a bad id.
