# Destructive Delete Flow Spec

## Job
Let a user remove something intentionally, with enough context and recovery to prevent accidental or unauthorized loss.

**Is the request a solution in disguise?**
Yes when "add confirmation" hides a better answer: undo, archive, permissions, dependency cleanup, or safer defaults.

## Actors & context
Owner, admin, collaborator, or support operator. Context may be urgent, emotionally charged, or high risk.

## Flow
```
Entry → [review target] → request delete → [confirm consequences] → destructive action → [deleted/recoverable] → next safe place
       ↓ failure             ↓ failure                 ↓ failure               ↓ failure
     cancel/back           permission path           edit/cancel             recover/undo
```

| Step | State | User can do | Failure branch | Reverse path |
| --- | --- | --- | --- | --- |
| Review target | Default/stale/error | Inspect item, dependencies, ownership | Item already deleted or changed | Back to list/detail |
| Request delete | Partial/permission-denied | Open confirmation, choose archive instead | User lacks permission | Back to review target |
| Confirm consequences | Default/empty/error | Read impact, type name if required, cancel | Required confirmation mismatch | Back to review target |
| Execute delete | Loading/slow/error | Wait, do not resubmit | Network fail, dependency lock, server reject | Back to confirmation with state preserved |
| Deleted state | Success/partial | Undo if available, view log, go to list | Undo window expired | Back to list or restored item |
| Recovery | Loading/error/success | Undo, restore, contact admin | Restore failed, permission changed | Back to deleted state |

## Primary action
Delete only after the user has seen the exact target, consequence, and recovery rule.

## States that exist in reality
- [x] Empty: no selected item or dependency list is empty
- [x] Cleared: target removed from current filtered list after delete
- [x] Loading: dependency check, delete request, undo request
- [x] Partial: some dependent records can be removed, others must transfer
- [x] Slow (>5s): large dependency graph or audit log write
- [x] Error: confirmation mismatch, delete failed, restore failed
- [x] Offline: cannot safely delete
- [x] Stale: item changed or was deleted elsewhere
- [x] Overflow: long item names, many dependencies, large audit details
- [x] Permission-denied: role cannot delete or restore

## Usually missed edge cases
- Item already deleted in another session
- User lacks delete permission but can archive
- Dependency prevents deletion
- Undo window expires while the user is reading
- Delete succeeds but audit log write is delayed
- Bulk delete has mixed permissions
- Typed confirmation target changes due to rename
- Offline user attempts deletion from stale UI

## Words
| Element | Copy |
| --- | --- |
| Primary button | Delete permanently |
| Empty state | Select an item before deleting. Nothing has been changed. |
| Error message | We could not delete this item. It may have changed or you may not have permission. |
| Success confirmation | Deleted. You can undo this for a limited time. |

## Success signal
The target is removed exactly once, the user lands somewhere coherent, and recovery is available or explicitly ruled out before deletion.

## Assumptions made without confirmation
Prefer undo or archive when product rules allow it. Permanent deletion requires explicit target confirmation.
