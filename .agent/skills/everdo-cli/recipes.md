# Common recipes

## Triage the inbox (hot path)

```
./everdo_cli.py list --list i --no-completed --json   # see what's there WITH notes
# Then batch-mutate. Use prefixes (first 4-6 hex of the id) to keep commands short:
./everdo_cli.py trash AB12 CD34 EF56              # bulk soft delete
./everdo_cli.py move --to next AB12 CD34          # bulk to Next
./everdo_cli.py assign --to <PROJECT_PREFIX> AB12 CD34    # bulk into a project
./everdo_cli.py complete AB12 CD34                # bulk complete
```

## Move several inbox items into a project at once

```
./everdo_cli.py assign --to <PROJECT_ID> <ID1> <ID2> <ID3>   # auto-promotes out of inbox
```

## Convert an inbox action into a project with subtasks

```
./everdo_cli.py convert --to p <ITEM_ID>          # action -> project
./everdo_cli.py move --to next <ITEM_ID>          # projects don't belong in inbox
./everdo_cli.py create "subtask 1" --parent <ITEM_ID> --list a
./everdo_cli.py create "subtask 2" --parent <ITEM_ID> --list m   # someday
```

## Convert an inbox action into a note inside an existing notebook

```
./everdo_cli.py convert --to n <ITEM_ID>          # action -> note
./everdo_cli.py assign --to <NOTEBOOK_ID> <ITEM_ID>    # auto-promotes out of inbox
```

