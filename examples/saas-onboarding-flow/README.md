# SaaS Onboarding Flow

First-time setup flow for a SaaS workspace admin who needs to invite teammates and connect one data source.

## Flow

Entry -> welcome -> invite teammates -> connect data source -> review -> dashboard-ready state

Failure paths:
- Invalid or duplicate invite keeps the user on the invite step with an inline recovery message.
- Billing connector intentionally fails once to demonstrate retry and recovery.
- Each setup step can be skipped and resumed later.

## Open

Open `index.html` in a browser. No build step is required.
