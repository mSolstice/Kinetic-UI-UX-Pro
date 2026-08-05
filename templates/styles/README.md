# Visual Style Constraint Sets

These files are generator inputs, not stylesheets. Each style defines ranges,
ratios, prohibitions, fallbacks, and accessibility constraints that feed token
generation and verification.

| Style | Intent | Best surfaces | Surfaces to avoid | Main accessibility risk |
| --- | --- | --- | --- | --- |
| `editorial` | Spacious, authored, and quietly opinionated | Landing pages, portfolios, case studies, longform content | Dense dashboards, admin tables, checkout, incident response | Text over imagery or excess whitespace can hide hierarchy |
| `brutalist` | Raw, immediate, and intentionally unpolished | Campaign pages, experimental portfolios, event microsites | Healthcare, finance, checkout, enterprise dashboards | Harsh hierarchy can harm reading order and state clarity |
| `swiss-grid` | Ordered, legible, and quietly authoritative | Dashboards, documentation, pricing, settings, data tables | Playful onboarding, immersive stories, games | Grid discipline can over-compress content if density is pushed |
| `soft-neumorphic` | Cushioned, quiet, and physically approachable | Wellness dashboards, personal productivity, ambient controls | Error-heavy forms, checkout, medical, finance, dense dashboards | Near-identical depth values cannot carry state meaning alone |
| `glass-layered` | Luminous, dimensional, and close to underlying content | Media browsers, map overlays, hero interfaces, creative tools | Data tables, financial dashboards, legal forms, text-heavy settings | Text over variable backgrounds can fail contrast without solid-surface fallback |
| `technical-dense` | Exact, operational, and built for repeated expert use | Admin tools, developer consoles, monitoring, data tables, editors | Consumer onboarding, marketing, checkout, wellness | High density can bury focus order, empty states, and error recovery |
| `warm-organic` | Humane, grounded, and welcoming | Wellness, food, education, community, creator portfolios | Security consoles, financial terminals, incident dashboards | Warm low-chroma palettes can become low contrast or monotonous |
| `high-contrast-utility` | Clear, durable, and usable under pressure | Forms, settings, admin tools, checkout, field workflows | Luxury brands, editorial stories, immersive marketing | Strong contrast can become visually loud without hierarchy discipline |
| `retro-terminal` | Nostalgic, focused, mechanical, and cinematic | Developer tools, security labs, technical demos, command palettes | Consumer checkout, medical, finance, longform reading | Traditional phosphor palettes and glow are often non-conformant |
| `luxury-minimal` | Restrained, premium, deliberate, and refined | Luxury commerce, portfolios, galleries, brand editorial | Admin tools, field workflows, dense dashboards, support queues | Minimalism can hide actions or produce low-contrast whisper text |
| `playful-rounded` | Friendly, buoyant, forgiving, and approachable | Onboarding, education, creator tools, consumer settings | Legal forms, trading, medical records, incident response | Playful color or motion can dilute serious status and destructive actions |
| `data-forward` | Trustworthy, legible, and oriented around comparison | Analytics, reporting, data tables, metrics grids, monitoring | Brand stories, immersive landing pages, playful onboarding | Chart meaning can become color-only without labels and patterns |
