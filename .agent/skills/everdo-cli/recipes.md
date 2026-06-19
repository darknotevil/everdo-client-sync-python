# Common recipes

## Triage the inbox (hot path)

```
everdo-cli --json item list --list inbox --no-completed   # see what's there WITH notes
# Then batch-mutate. Use prefixes (first 4-6 hex of the id) to keep commands short:
everdo-cli item trash AB12 CD34 EF56             # bulk soft delete
everdo-cli item complete AB12 CD34               # bulk complete
# Field changes are per-item (item set is single-id); loop for several:
for id in AB12 CD34; do everdo-cli item set "$id" --list next; done       # bulk to Next
for id in AB12 CD34; do everdo-cli item set "$id" --parent <PROJECT_PREFIX>; done  # into a project
```

## Move several inbox items into a project at once

```
for id in <ID1> <ID2> <ID3>; do everdo-cli item set "$id" --parent <PROJECT_ID>; done   # auto-promotes out of inbox
```

## Convert an inbox action into a project with subtasks

```
everdo-cli item set <ITEM_ID> --type project --list next   # convert + get it out of inbox in one call
everdo-cli item create "subtask 1" --parent <ITEM_ID> --list next
everdo-cli item create "subtask 2" --parent <ITEM_ID> --list someday
```

## Convert an inbox action into a note inside an existing notebook

```
everdo-cli item set <ITEM_ID> --type note --parent <NOTEBOOK_ID>   # convert + attach (auto-promotes out of inbox)
```

## Tag a batch of items

```
everdo-cli tag list                              # find the exact tag title first
for id in AB12 CD34; do everdo-cli item tag add "$id" finance; done
everdo-cli item list --tag finance               # verify
```
