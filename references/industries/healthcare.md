# Healthcare

## Primary User Goal

Users are trying to understand care instructions, book or manage care, enter clinical information, or make decisions while anxious, distracted, fatigued, or physically impaired. The interface must reduce ambiguity and preserve context.

## Trust Requirements

At the moment of decision, show patient identity, date/time, care context, units, clinician/source, status, privacy boundary, and whether the information is advice, instruction, result, draft, or administrative data.

## Error Costs

High-cost mistakes include wrong patient, wrong dose, wrong unit, missed appointment, hidden contraindication, incorrect insurance assumption, or sending sensitive data to the wrong recipient. Concrete failure mode: a dosage field without unit confirmation.

## Density Expectations

Medium density. Clinical or administrative screens need enough context to prevent wrong-patient or wrong-unit errors, but forms must remain readable for stressed users. Avoid dense visual treatment for patient-facing care instructions.

## Motion Budget

Very low. Use motion only for state changes like saving, uploading, or step progression. Avoid decorative motion, large spatial transitions, and anything that distracts from instructions or warnings.

## Style Fit

Suitable: `high-contrast-utility`, `swiss-grid`, `data-forward`, `warm-organic` for supportive patient education.

Conflicts: `brutalist`, `retro-terminal`, `glass-layered`, `soft-neumorphic` when depth or transparency reduces state clarity, and `playful-rounded` for serious clinical decisions.

## Often Forgotten States

- Wrong-patient prevention
- Unit confirmation and unit conversion
- Partial lab result availability
- Provider delayed response
- Permission-denied record sections
- Expired appointment slot
- Insurance eligibility unknown
- Upload failed but draft preserved

## Domain-Specific Failure Modes

- Dosage input accepts a number without unit confirmation
- Appointment slot remains selectable after it expires
- Lab result appears without collected date or reference context
- Patient portal hides which family member/profile is active
- Message composer does not distinguish urgent from non-urgent contact
- Medication list cannot show discontinued or historical items clearly

## complianceConsiderations

This is orientation, not legal advice. Requirements vary by jurisdiction and must be verified with qualified legal, clinical, privacy, security, and accessibility professionals.

Categories that typically apply include health information privacy, consent, clinical safety, data security, audit trails, identity and access control, accessibility, records retention, and medical-device or clinical-decision boundaries where relevant.

Questions to ask a qualified professional:

- What data is protected health information in this flow?
- What consent, access, and proxy-user rules apply?
- Which clinical values require unit, range, source, or timestamp display?
- What audit log and breach-response evidence must be retained?
- Is the product giving information, care coordination, or regulated clinical guidance?
