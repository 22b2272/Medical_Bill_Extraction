import unittest

from app.schemas import BillItem, PagewiseLineItems
from app.validation import BillValidator


class BillValidatorTests(unittest.TestCase):
    def test_warns_when_amount_does_not_match_rate_times_quantity(self) -> None:
        page = PagewiseLineItems(
            page_no=1,
            page_type="Bill Detail",
            bill_items=[
                BillItem(
                    item_name="Consultation",
                    item_amount=12.0,
                    item_rate=5.0,
                    item_quantity=2.0,
                )
            ],
        )

        warnings = BillValidator.validate_items(page)

        self.assertEqual(len(warnings), 1)
        self.assertIn("Page 1", warnings[0])

    def test_finds_exact_duplicates_across_pages(self) -> None:
        item = BillItem(
            item_name="  Room   charge ",
            item_amount=100.0,
            item_rate=100.0,
            item_quantity=1.0,
        )
        pages = [
            PagewiseLineItems(
                page_no=1, page_type="Bill Detail", bill_items=[item]
            ),
            PagewiseLineItems(
                page_no=2,
                page_type="Final Bill",
                bill_items=[
                    BillItem(
                        item_name="room charge",
                        item_amount=100.0,
                        item_rate=100.0,
                        item_quantity=1.0,
                    )
                ],
            ),
        ]

        warnings = BillValidator.detect_duplicates(pages)

        self.assertEqual(len(warnings), 1)
        self.assertIn("Possible repeated line item", warnings[0])

    def test_does_not_report_repeated_items_within_one_page_as_cross_page(self) -> None:
        item = BillItem(
            item_name="Lab test",
            item_amount=50.0,
            item_rate=50.0,
            item_quantity=1.0,
        )
        page = PagewiseLineItems(
            page_no=1,
            page_type="Bill Detail",
            bill_items=[item, item],
        )

        self.assertEqual(BillValidator.detect_duplicates([page]), [])


if __name__ == "__main__":
    unittest.main()
