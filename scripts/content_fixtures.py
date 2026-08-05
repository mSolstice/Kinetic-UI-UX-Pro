#!/usr/bin/env python3
"""Generate realistic hostile content fixtures for UI layout testing."""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

SHAPES = {
    "person-names", "company-names", "product-titles", "addresses",
    "email-addresses", "prices", "dates", "durations", "file-names",
    "paragraph-body-copy",
}
ALIASES = {
    "person": "person-names",
    "people": "person-names",
    "person-names": "person-names",
    "company": "company-names",
    "companies": "company-names",
    "company-names": "company-names",
    "product": "product-titles",
    "products": "product-titles",
    "product-titles": "product-titles",
    "address": "addresses",
    "addresses": "addresses",
    "email": "email-addresses",
    "emails": "email-addresses",
    "email-addresses": "email-addresses",
    "price": "prices",
    "prices": "prices",
    "date": "dates",
    "dates": "dates",
    "duration": "durations",
    "durations": "durations",
    "file": "file-names",
    "files": "file-names",
    "file-names": "file-names",
    "paragraph": "paragraph-body-copy",
    "body": "paragraph-body-copy",
    "paragraph-body-copy": "paragraph-body-copy",
}
RTL_MARK = "\u200f"


def normalize_shape(shape: str) -> str:
    key = shape.strip().lower().replace("_", "-")
    if key not in ALIASES:
        raise SystemExit(f"unknown shape '{shape}'. Available: {', '.join(sorted(SHAPES))}")
    return ALIASES[key]


def expanded(text: str, factor=1.4) -> str:
    words = text.split()
    out = list(words)
    i = 0
    while len(" ".join(out)) < int(len(text) * factor):
        out.append(words[i % len(words)])
        i += 1
    return " ".join(out)


def base_values(shape: str, locale: str):
    if shape == "person-names":
        return [
            ("shortest", "Bo", False),
            ("longest", "María-José Carreño Quiñones de la Vega-Santamaría", False),
            ("diacritics", "Zoë François Łukaszewicz", False),
            ("cjk", "王小明", False),
            ("arabic-rtl", f"{RTL_MARK}ليلى بنت عبد الرحمن الخالدي", False),
            ("forty-percent-expansion", expanded("Alexandra Morgan", 1.4), False),
            ("optional-null-middle-name", None, True),
        ]
    if shape == "company-names":
        return [
            ("shortest", "Ko", False),
            ("longest", "International Consolidated Renewable Infrastructure Holdings Cooperative", False),
            ("diacritics", "Crème Brûlée Atelier Société", False),
            ("cjk", "東京未来物流株式会社", False),
            ("arabic-rtl", f"{RTL_MARK}شركة الرافدين للخدمات الرقمية", False),
            ("forty-percent-expansion", expanded("Northstar Analytics Group", 1.4), False),
            ("optional-null-legal-name", None, True),
        ]
    if shape == "product-titles":
        return [
            ("shortest", "USB-C Hub", False),
            ("longest", "Commercial-grade refrigerated medication cabinet with audit logging and dual temperature probes", False),
            ("diacritics", "Café-grade espresso scale with crème timer", False),
            ("cjk", "省電力ワイヤレス温湿度センサー", False),
            ("arabic-rtl", f"{RTL_MARK}حاسوب محمول للأعمال مع ضمان ممتد", False),
            ("forty-percent-expansion", expanded("Noise-cancelling warehouse headset", 1.4), False),
            ("optional-null-subtitle", None, True),
        ]
    if shape == "addresses":
        return [
            ("shortest", "7 Oak St", False),
            ("longest", "Building 14, Dock C, 9876 Northeast Industrial Logistics Parkway, Suite 1200B, Springfield, IL 62704-1299", False),
            ("diacritics", "18 Rue de l'Église, São Paulo, SP 01000-000", False),
            ("cjk", "〒160-0022 東京都新宿区新宿三丁目38番1号", False),
            ("arabic-rtl", f"{RTL_MARK}شارع الملك فهد، مبنى ٢٤، الدور الخامس، الرياض", False),
            ("forty-percent-expansion", expanded("421 Market Street, Unit 9B, San Francisco CA", 1.4), False),
            ("optional-null-address-line-2", None, True),
        ]
    if shape == "email-addresses":
        return [
            ("shortest", "a@b.co", False),
            ("longest", "procurement.escalations+medical-cold-chain-northeast-region@example-operations.internal", False),
            ("diacritics", "zoe.francois@example.com", False),
            ("cjk-local-part", "user+東京@example.jp", False),
            ("arabic-domain", "support@xn--mgbh0fb.xn--kgbechtv", False),
            ("forty-percent-expansion", "alexandra.morgan.longlabel+notifications@example-company.com", False),
            ("optional-null-secondary-email", None, True),
        ]
    if shape == "prices":
        return price_values(locale)
    if shape == "dates":
        today = date(2026, 8, 5)
        return [
            ("shortest", format_date(today, locale), False),
            ("longest", format_date(today + timedelta(days=185), locale, long=True), False),
            ("diacritics", "miércoles, 5 de agosto de 2026", False),
            ("cjk", "2026年8月5日水曜日", False),
            ("arabic-rtl", f"{RTL_MARK}الأربعاء، ٥ أغسطس ٢٠٢٦", False),
            ("forty-percent-expansion", expanded(format_date(today, locale, long=True), 1.4), False),
            ("optional-null-completion-date", None, True),
        ]
    if shape == "durations":
        return [
            ("shortest", "4 min", False),
            ("longest", "13 weeks, 6 days, 23 hours, and 45 minutes remaining", False),
            ("diacritics", "2 h 15 min d’attente estimée", False),
            ("cjk", "残り2時間15分", False),
            ("arabic-rtl", f"{RTL_MARK}ساعتان و١٥ دقيقة متبقية", False),
            ("forty-percent-expansion", expanded("Estimated processing time is 45 minutes", 1.4), False),
            ("optional-null-duration", None, True),
        ]
    if shape == "file-names":
        return [
            ("shortest", "a.pdf", False),
            ("longest", "2026-warehouse-safety-audit-final-reviewed-approved-with-appendices-and-signatures-v17.pdf", False),
            ("diacritics", "résumé_José_García_final.pdf", False),
            ("cjk", "顧客別_請求書_最終版.xlsx", False),
            ("arabic-rtl", f"{RTL_MARK}تقرير_المخزون_النهائي.pdf", False),
            ("forty-percent-expansion", expanded("quarterly-board-report-final.pdf", 1.4).replace(" ", "-"), False),
            ("optional-null-attachment-name", None, True),
        ]
    return [
        ("shortest", "Done.", False),
        ("longest", "This order is waiting for carrier confirmation because one refrigerated item requires manual release from the overnight receiving team before it can leave the dock.", False),
        ("diacritics", "Crème fraîche, jalapeño, São Paulo, and Zürich all appear in real customer notes.", False),
        ("cjk", "この説明文は、複数行の折り返しと読みやすい行間を確認するためのものです。", False),
        ("arabic-rtl", f"{RTL_MARK}هذه رسالة طويلة لاختبار التفاف النص واتجاه القراءة داخل الواجهة.", False),
        ("forty-percent-expansion", expanded("The customer changed the delivery window after the route was already assigned.", 1.4), False),
        ("optional-null-description", None, True),
    ]


def price_values(locale: str):
    values = [0, 1.2, 1234.56, 9876543.21, -42.5]
    labels = ["zero", "shortest", "standard", "longest", "negative-adjustment"]
    rows = [(label, format_price(value, locale), False) for label, value in zip(labels, values)]
    rows += [
        ("diacritics", f"Prix réglé: {format_price(1234.56, 'fr-FR')}", False),
        ("cjk-locale-reference", format_price(1234.56, "ja-JP"), False),
        ("arabic-rtl", f"{RTL_MARK}{format_price(1234.56, 'ar-SA')}", False),
        ("forty-percent-expansion", expanded(format_price(1234.56, locale), 1.4), False),
        ("optional-null-discount", None, True),
    ]
    return rows


def format_price(value: float, locale: str) -> str:
    locale = locale.lower()
    if locale.startswith("fr"):
        amount = f"{abs(value):,.2f}".replace(",", " ").replace(".", ",")
        sign = "-" if value < 0 else ""
        return f"{sign}{amount} €"
    if locale.startswith("de") or locale.startswith("es"):
        amount = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        sign = "-" if value < 0 else ""
        return f"{sign}{amount} EUR" if locale.startswith("de") else f"{sign}{amount} €"
    if locale.startswith("ja"):
        return f"¥{round(value):,}"
    if locale.startswith("ar"):
        amount = f"{abs(value):,.2f}"
        sign = "-" if value < 0 else ""
        return f"{sign}{amount} ر.س"
    if locale.startswith("en-gb"):
        return f"£{value:,.2f}"
    return f"${value:,.2f}"


def format_date(value: date, locale: str, long=False) -> str:
    locale = locale.lower()
    if locale.startswith("de"):
        return value.strftime("%d.%m.%Y") if not long else value.strftime("%A, %d. %B %Y")
    if locale.startswith("en-gb"):
        return value.strftime("%d/%m/%Y") if not long else value.strftime("%A, %d %B %Y")
    if locale.startswith("ja"):
        return f"{value.year}年{value.month}月{value.day}日"
    if locale.startswith("ar"):
        return f"{RTL_MARK}{value.year}/{value.month:02d}/{value.day:02d}"
    return value.strftime("%m/%d/%Y") if not long else value.strftime("%A, %B %d, %Y")


def empty_state(shape: str):
    return {
        "person-names": "No people added yet. Invited teammates and saved contacts will appear here.",
        "company-names": "No companies yet. Accounts you create or import will appear here.",
        "product-titles": "No products yet. Published and draft products will appear here once they are added.",
        "addresses": "No saved addresses yet. Delivery and billing addresses will appear here.",
        "email-addresses": "No email addresses yet. Verified contact emails will appear here.",
        "prices": "No charges yet. Prices, discounts, and totals will appear here once items are added.",
        "dates": "No dates scheduled yet. Upcoming deadlines and completed milestones will appear here.",
        "durations": "No time tracked yet. Active and completed durations will appear here.",
        "file-names": "No files uploaded yet. Accepted files and failed uploads will appear here.",
        "paragraph-body-copy": "No notes yet. Saved notes and status updates will appear here.",
    }[shape]


def make_rows(shape: str, count: int, locale: str, edge_only=False, empty_states=False):
    if empty_states:
        return [{
            "shape": shape,
            "locale": locale,
            "kind": "empty-state",
            "value": empty_state(shape),
            "optional": False,
            "direction": "rtl" if locale.lower().startswith("ar") else "ltr",
        }]
    base = base_values(shape, locale)
    rows = []
    for kind, value, optional in base:
        rows.append(row(shape, locale, kind, value, optional))
    if edge_only:
        return rows
    i = 0
    while len(rows) < count:
        kind, value, optional = base[i % len(base)]
        suffix = "" if value is None else f" #{(i // len(base)) + 2}"
        rows.append(row(shape, locale, f"realistic-{i + 1}", None if value is None else f"{value}{suffix}", optional))
        i += 1
    return rows[:count]


def row(shape, locale, kind, value, optional):
    direction = "rtl" if value and any("\u0600" <= ch <= "\u06ff" for ch in str(value)) else "ltr"
    return {
        "shape": shape,
        "locale": locale,
        "kind": kind,
        "value": value,
        "optional": optional,
        "direction": direction,
        "notes": notes_for(kind, optional),
    }


def notes_for(kind, optional):
    notes = []
    if kind == "forty-percent-expansion":
        notes.append("approximately 40 percent longer than a typical English string")
    if "rtl" in kind or "arabic" in kind:
        notes.append("right-to-left sample")
    if optional:
        notes.append("optional field intentionally missing")
    return notes


def command_generate(args):
    shape = normalize_shape(args.shape)
    rows = make_rows(shape, args.count, args.locale, args.edge_cases_only, args.empty_states)
    print(json.dumps({
        "shape": shape,
        "locale": args.locale,
        "count": len(rows),
        "edgeCasesOnly": bool(args.edge_cases_only),
        "emptyStates": bool(args.empty_states),
        "fixtures": rows,
    }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="generate hostile realistic content fixtures")
    gen.add_argument("--shape", required=True)
    gen.add_argument("--count", type=int, default=12)
    gen.add_argument("--locale", default="en-US")
    gen.add_argument("--edge-cases-only", action="store_true")
    gen.add_argument("--empty-states", action="store_true")
    gen.set_defaults(func=command_generate)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
