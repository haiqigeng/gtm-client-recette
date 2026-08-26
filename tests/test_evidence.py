from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evidence import build_gtm_evidence, decode_ga4_requests


class EvidenceTests(unittest.TestCase):
    def test_tag_names_and_values_are_normalized_from_bounded_carrier_row(self) -> None:
        raw = {
            "rows": [
                {"cursor": 7, "panel_text": "", "tags": []},
                {
                    "cursor": 9,
                    "panel_text": "Tags Fired\nGA4 ecommerce\nTags Not Fired",
                    "tags": [
                        {
                            "name": "GA4 ecommerce",
                            "fired": True,
                            "detail_text": "fired 1 time",
                            "names": {"Event Name": "view_item", "ecommerce": "Data Layer"},
                            "values": {
                                "Event Name": "view_item",
                                "ecommerce": '{items:[{item_name:"Iron",quantity:1}],currency:"EUR"}',
                            },
                        }
                    ],
                },
            ]
        }
        source = {"complete": True, "selected": {"cursor": 7}}
        gtm = build_gtm_evidence(raw, source)
        self.assertTrue(gtm["complete"])
        self.assertTrue(gtm["tags"][0]["concerned"])
        self.assertEqual(gtm["tags"][0]["event_cursor"], 9)
        self.assertEqual(gtm["tags"][0]["runtime"]["ecommerce"]["currency"], "EUR")

    def test_direct_post_batch_and_first_party_protocol_hits_decode(self) -> None:
        records = [
            {
                "url": "https://www.google-analytics.com/g/collect?v=2&tid=G-TEST&en=view_item&ep.currency=EUR",
                "method": "GET",
                "post_data": None,
                "status": 204,
                "failed": False,
            },
            {
                "url": "https://metrics.example.test/proxy?v=2&tid=G-TEST",
                "method": "POST",
                "post_data": "en=purchase&epn.value=42\nen=add_to_cart&pr1=idSKU~nmIron~qt2",
                "status": 204,
                "failed": False,
            },
        ]
        view = decode_ga4_requests(records, "view_item")
        purchase = decode_ga4_requests(records, "purchase")
        cart = decode_ga4_requests(records, "add_to_cart")
        self.assertEqual(view["requests"][0]["parameters"]["currency"], "EUR")
        self.assertEqual(purchase["requests"][0]["parameters"]["value"], 42)
        self.assertEqual(cart["requests"][0]["parameters"]["items"][0]["quantity"], 2)

    def test_failed_and_duplicate_hits_remain_visible(self) -> None:
        record = {
            "url": "https://first.party.test/a?v=2&tid=G-TEST&en=newsletter",
            "method": "POST",
            "post_data": "ep.position=footer",
            "status": None,
            "failed": True,
            "failure": "blocked",
        }
        decoded = decode_ga4_requests([record, dict(record)], "newsletter")
        self.assertTrue(decoded["complete"])
        self.assertEqual(len(decoded["requests"]), 2)
        self.assertTrue(all(hit["failed"] for hit in decoded["requests"]))
        self.assertTrue(all(hit["duplicate"] for hit in decoded["requests"]))


if __name__ == "__main__":
    unittest.main()
