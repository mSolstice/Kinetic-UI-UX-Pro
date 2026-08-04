# Auth Flow Spec

## Job
Let a known or new user enter the product securely without losing their work or getting trapped by provider/account ambiguity.

**Is the request a solution in disguise?**
Often. "Build login" may mean session recovery, account creation, password reset, SSO routing, or preserving a gated destination.

## Actors & context
First-time visitor, returning user, invited teammate, admin-enforced SSO user, or locked-out user. Context may be urgent and mobile.

## Flow
```
Entry → [identify] → submit identifier → [choose credential path] → authenticate → [session ready] → destination
                    ↓ failure                               ↓ failure                    ↓ failure
                  recover input                           recover credential           recover session
```

| Step | State | User can do | Failure branch | Reverse path |
| --- | --- | --- | --- | --- |
| Gated entry | Empty/unauthenticated | Sign in, create account, continue with provider | Destination unknown or expired invite | Back to prior page or public landing |
| Identify user | Default/loading/error | Enter email or provider | Invalid email, offline, rate-limited retry | Back to gated entry |
| Account routing | Partial/success/error | Choose password, magic link, SSO, or provider | Account exists with different provider; SSO required | Back to edit email |
| Password/provider auth | Loading/error/success | Submit credential or provider consent | Wrong password, provider denied, MFA required | Back to account routing |
| Reset password | Empty/loading/error/success | Request reset, open reset link, set new password | Expired reset link, reused token, weak password | Back to sign in or request new link |
| MFA/challenge | Partial/loading/error | Enter code or recovery key | Code expired, too many attempts | Back to credential path or recovery options |
| Session handoff | Loading/stale/error/success | Continue to destination | Session write failed, invite revoked, destination denied | Back to authenticated home or sign out |

## Primary action
Continue with the safest available credential path for the identified account.

## States that exist in reality
- [x] Empty: no identifier entered
- [x] Cleared: user edits email after routed credential path
- [x] Loading: identifier lookup, provider redirect, password submit, reset submit
- [x] Partial: email known but credential challenge incomplete
- [x] Slow (>5s): SSO/provider redirect or email delivery delay
- [x] Error: invalid credential, provider mismatch, expired token
- [x] Offline: cannot submit or verify challenge
- [x] Stale: reset link, invite, session, or MFA code expired
- [x] Overflow: long email/provider names, many SSO tenants
- [x] Permission-denied: account disabled, SSO enforced, invite revoked

## Usually missed edge cases
- Account exists with different provider
- Expired reset link
- Rate-limited retry
- Email link opened on a different device
- Provider returns an unverified email
- User is authenticated but lacks permission for the intended destination
- Existing session belongs to another account
- MFA device unavailable

## Words
| Element | Copy |
| --- | --- |
| Primary button | Continue |
| Empty state | Enter your email to find the right sign-in method. |
| Error message | We could not verify that sign-in. Check the method and try again. |
| Success confirmation | You are signed in. Taking you back to your work. |

## Success signal
The user reaches the intended destination with a valid session, or lands on a clear recovery path without losing context.

## Assumptions made without confirmation
Email is the account identifier. Provider routing is server-determined. Password reset links can expire and be resent.
