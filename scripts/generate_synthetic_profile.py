#!/usr/bin/env python3
"""Generate deterministic, non-personal synthetic form data for authorised tests."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime

PROFILES = {
    "fr-FR": {
        "first_name": "Recette",
        "last_name": "Test",
        "address_line_1": "1 rue Exemple",
        "city": "Ville Test",
        "postal_code": "75000",
        "country": "France",
    },
    "en-GB": {
        "first_name": "Recette",
        "last_name": "Test",
        "address_line_1": "1 Example Street",
        "city": "Test Town",
        "postal_code": "TE1 1ST",
        "country": "United Kingdom",
    },
    "en-US": {
        "first_name": "Recette",
        "last_name": "Test",
        "address_line_1": "1 Example Street",
        "city": "Test City",
        "postal_code": "00000",
        "country": "United States",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", required=True, help="Stable run or journey identifier.")
    parser.add_argument("--locale", choices=tuple(PROFILES), default="fr-FR")
    parser.add_argument(
        "--include-phone",
        action="store_true",
        help="Include a reserved fictional +1 202-555-01xx number.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    digest = hashlib.sha256(args.seed.encode("utf-8")).hexdigest()
    suffix = int(digest[:6], 16) % 10000
    phone_suffix = int(digest[6:10], 16) % 100
    profile = dict(PROFILES[args.locale])
    profile.update(
        {
            "synthetic": True,
            "locale": args.locale,
            "email": f"recette+{suffix:04d}@example.com",
            "username": f"recette-test-{suffix:04d}",
            "date_of_birth": "1990-01-01",
            "company": "Example Test Organisation",
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "password_instruction": "Generate in the protected browser field; never record it.",
        }
    )
    if args.include_phone:
        profile["phone"] = f"+1 202-555-01{phone_suffix:02d}"
        profile["phone_note"] = (
            "Reserved fictional 555-01xx format. Use a client-provided test range "
            "if the form rejects international numbers."
        )
    print(json.dumps(profile, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
