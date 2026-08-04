# Search Refine Flow Spec

## Job
Help the user narrow a broad result set into a trustworthy answer or item without losing query context.

**Is the request a solution in disguise?**
Often. "Add filters" may mean ranking is weak, result labels are unclear, or the user needs comparison.

## Actors & context
Researcher, shopper, operator, support agent, or daily power user. Context may include urgency and repeated refinement.

## Flow
```
Entry → [empty query] → search → [results] → refine/filter/sort → [narrowed results] → select → outcome
                    ↓ failure       ↓ failure              ↓ failure              ↓ failure
                  edit query      recover search         clear/refine less       back to results
```

| Step | State | User can do | Failure branch | Reverse path |
| --- | --- | --- | --- | --- |
| Empty query | Empty/default | Type, use recent search, browse categories | No recent searches | Back to prior page |
| Searching | Loading/slow/offline | Wait, cancel, edit query | Timeout, offline, API error | Back to empty query with text preserved |
| Results | Success/overflow/stale | Scan, sort, refine, open result | Too many results, stale index | Back to edit query |
| No results | Cleared/error | Clear filters, broaden query, save alert | Query too narrow, filters conflict | Back to results before filters |
| Refinement | Partial/loading/success | Add/remove filters, sort, compare | Filter count explosion, unavailable facet | Back to previous filter state |
| Result detail | Loading/error/success | Inspect, compare, act | Result deleted or permission denied | Back to same result position |
| Outcome | Success/partial | Save, purchase, assign, export | Action fails after selection | Back to result detail |

## Primary action
Select the best matching result or confidently broaden the search.

## States that exist in reality
- [x] Empty: no query or no recent searches
- [x] Cleared: filters produce no results
- [x] Loading: search, facet counts, detail fetch
- [x] Partial: some facets loaded, some unavailable
- [x] Slow (>5s): large index or remote provider
- [x] Error: search endpoint failed
- [x] Offline: cached recent searches only
- [x] Stale: result changed since indexing
- [x] Overflow: too many results, long titles, many facets
- [x] Permission-denied: result exists but cannot be opened

## Usually missed edge cases
- Filter combination clears all results
- Result disappears after being opened
- Sort changes while user is comparing items
- Facet counts arrive after results
- Query typo produces plausible but wrong results
- Long result titles break the row layout
- Back button loses filter state
- Permission-denied result appears in search

## Words
| Element | Copy |
| --- | --- |
| Primary button | Search |
| Empty state | Search by name, keyword, or category to start narrowing results. |
| Error message | Search is unavailable. Your query is still here; try again. |
| Success confirmation | Results updated. |

## Success signal
The user reaches a selected result or a clearly explained no-results state with query and filters preserved.

## Assumptions made without confirmation
Query, filters, sort, and scroll position should be restorable through back navigation where the host supports it.
