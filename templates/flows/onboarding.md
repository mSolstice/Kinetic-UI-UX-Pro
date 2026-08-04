# Onboarding Flow Spec

## Job
Help a new user reach first value quickly while collecting only the setup information needed for that first useful outcome.

**Is the request a solution in disguise?**
Usually. "Add onboarding" may mean activation, permissions, import, team invite, or personalization.

## Actors & context
New account owner, invited collaborator, trial user, or returning user who abandoned setup. Context ranges from curious to evaluation-driven.

## Flow
```
Welcome → [intent] → choose goal → [setup] → connect/import/invite → [first workspace] → first action → activated
          ↓ failure                 ↓ failure              ↓ failure             ↓ failure
        skip/retry                edit goal               manual fallback       resume later
```

| Step | State | User can do | Failure branch | Reverse path |
| --- | --- | --- | --- | --- |
| Welcome | Empty/default | Start, skip, resume existing setup | Session stale or invite revoked | Back to product home/sign in |
| Goal selection | Default/partial/empty | Pick goal or role | No matching goal | Back to welcome |
| Setup details | Partial/loading/error | Add project/team/preferences | Validation failure, permission denied | Back to goal selection |
| Connect/import | Loading/slow/error/success | Connect tool, upload file, skip | Provider denied, file invalid, timeout | Back to setup or manual entry |
| Invite team | Empty/partial/error/success | Add teammates or skip | Invalid emails, domain restriction | Back to setup |
| First workspace | Loading/stale/error/success | Review generated setup | Seed data failed or stale | Back to connect/import |
| First action | Default/error/success | Complete guided task | User lacks permission or action fails | Back to workspace overview |

## Primary action
Continue setup until the user reaches a real first action.

## States that exist in reality
- [x] Empty: no goal, no team, no imported data
- [x] Cleared: user removes all selected goals or invited teammates
- [x] Loading: workspace creation, import, integration connect
- [x] Partial: some setup completed, not activated
- [x] Slow (>5s): import or generated workspace
- [x] Error: invalid input, failed provider, failed seed
- [x] Offline: cannot save progress
- [x] Stale: invitation or setup draft expired
- [x] Overflow: many goals, many team emails, large imports
- [x] Permission-denied: invited role cannot configure workspace

## Usually missed edge cases
- User returns after abandoning midway
- Invited teammate cannot access owner-only setup step
- Integration permission denied after provider consent
- Import succeeds partially
- User wants to skip without losing the ability to finish later
- Empty account after all suggested templates are dismissed
- Trial expired during onboarding

## Words
| Element | Copy |
| --- | --- |
| Primary button | Continue setup |
| Empty state | Choose a goal so we can set up the first useful workspace. |
| Error message | We could not save this step. Your previous progress is still available. |
| Success confirmation | Setup saved. Your workspace is ready for the first action. |

## Success signal
The user completes one meaningful in-product action, not merely the setup screens.

## Assumptions made without confirmation
Every step is resumable. Skip is allowed but keeps a visible path back to setup.
