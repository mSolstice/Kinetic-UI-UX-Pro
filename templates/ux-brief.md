# UX Brief — fill before building

Keep this to one screen. If it takes longer than five minutes, the scope is too large.

## Job
What is the user actually trying to accomplish, in their words?
> 

**Is the request a solution in disguise?** (e.g. "add a filter" may mean "I can't find things")
> 

## Actors & context
Who, on what device, under what pressure?
> 

First-time or daily? Calm or urgent? One-handed or desk?
> 

## Flow
```
Entry → [state] → action → [state] → outcome
                    ↓ failure
                  [recovery]
```
> 

## Primary action
One per view. Everything else subordinate.
> 

## States that exist in reality
- [ ] Empty (never had data)
- [ ] Cleared (filtered to nothing)
- [ ] Loading
- [ ] Partial
- [ ] Slow (>5s)
- [ ] Error
- [ ] Offline
- [ ] Stale
- [ ] Overflow (long strings, huge numbers, 500 rows)
- [ ] Permission-denied

## Words (write these before layout)
| Element | Copy |
|---|---|
| Primary button | |
| Empty state | |
| Error message | |
| Success confirmation | |

## Success signal
What observable behavior means this worked?
> 

## Assumptions made without confirmation
> 
