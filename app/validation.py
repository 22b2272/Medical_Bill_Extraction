import re
from decimal import Decimal

from .schemas import PagewiseLineItems


class BillValidator:
    """Non-blocking consistency checks for extracted bill items."""

    @staticmethod
    def validate_items(page_data: PagewiseLineItems) -> list[str]:
        warnings: list[str] = []
        for index, item in enumerate(page_data.bill_items, start=1):
            expected_amount = Decimal(str(item.item_rate)) * Decimal(
                str(item.item_quantity)
            )
            actual_amount = Decimal(str(item.item_amount))
            if abs(expected_amount - actual_amount) > Decimal("0.01"):
                warnings.append(
                    f"Page {page_data.page_no}, item {index} "
                    f"({item.item_name}): rate × quantity is {expected_amount}, "
                    f"but amount is {actual_amount}"
                )
        return warnings

    @staticmethod
    def detect_duplicates(pages: list[PagewiseLineItems]) -> list[str]:
        seen_pages: dict[tuple[str, Decimal], set[int]] = {}
        warned_items: set[tuple[str, Decimal]] = set()
        duplicates: list[str] = []
        for page in pages:
            for item in page.bill_items:
                normalized_name = re.sub(r"\s+", " ", item.item_name).strip().casefold()
                key = (normalized_name, Decimal(str(item.item_amount)))
                page_numbers = seen_pages.setdefault(key, set())
                is_repeated_on_another_page = (
                    bool(page_numbers)
                    and page.page_no not in page_numbers
                    and key not in warned_items
                )
                if is_repeated_on_another_page:
                    duplicates.append(
                        f"Possible repeated line item across pages: {item.item_name}"
                    )
                    warned_items.add(key)
                page_numbers.add(page.page_no)
        return duplicates
