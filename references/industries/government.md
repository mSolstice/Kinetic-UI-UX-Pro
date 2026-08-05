# Government

## Primary User Goal

Users are trying to apply, report, pay, renew, appeal, or retrieve public services while under legal, financial, language, device, time, or documentation pressure. Failure can block essential services.

## Trust Requirements

At the moment of decision, show agency/service identity, eligibility scope, required documents, deadline, fees, saved progress, submission receipt, appeal/retry path, language access, and support channel.

## Error Costs

High-cost mistakes include missed benefits, wrong filing, payment to wrong service, incomplete submission, inaccessible form, or lost progress on a shared device. Concrete failure mode: a form that cannot be completed on a shared low-spec device.

## Density Expectations

Medium density with plain hierarchy. Forms need step clarity and recovery; eligibility and document requirements must be visible before users invest effort.

## Motion Budget

Near-zero. Motion should not be required to understand progress or success. Avoid expressive animation, parallax, large transitions, and anything that performs poorly on low-spec devices.

## Style Fit

Suitable: `high-contrast-utility`, `swiss-grid`, `data-forward` for public dashboards, `warm-organic` only for outreach/education pages with strict contrast.

Conflicts: `glass-layered`, `soft-neumorphic`, `brutalist`, `luxury-minimal`, `retro-terminal`, and `playful-rounded` for essential service forms.

## Often Forgotten States

- Save and resume across shared devices
- Expired session with draft recovery
- Missing document checklist
- Ineligible but redirectable
- Language switch mid-flow
- Low bandwidth or old browser
- Payment pending or receipt unavailable
- Appeal or correction path

## Domain-Specific Failure Modes

- Form requires modern device performance or persistent browser storage
- Required document appears only after several steps
- Session timeout loses entered data without warning
- Uploaded document fails silently
- Confirmation page lacks receipt number and next step
- Language switch resets the form

## complianceConsiderations

This is orientation, not legal advice. Requirements vary by jurisdiction and must be verified with qualified legal, accessibility, procurement, privacy, records, and security professionals.

Categories that typically apply include accessibility, public records, identity proofing, privacy, security, language access, payments, procurement, retention, and service eligibility rules.

Questions to ask a qualified professional:

- Which accessibility and language-access obligations govern this service?
- What identity proofing and data minimization rules apply?
- What receipt, appeal, correction, and records-retention requirements exist?
- What devices, browsers, and offline/shared-device constraints must be supported?
- What public-sector security and procurement standards are mandatory?
