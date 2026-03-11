# gstr1_parser.py

from typing import Dict, List

# BUG FIX: Import from flat module name 'gstr1', not 'schemas.gstr1'
from schemas.gstr1 import (
    Gstr1AdvanceEntry,
    Gstr1AdvanceItem,
)


def parse_gstr1_advance_tax(payload: Dict) -> List[Gstr1AdvanceEntry]:
    """
    Converts the GST sandbox response for GSTR1 AT into a cleaner internal structure.

    Actual response shape (confirmed from return_structures.py):
      payload["data"]["data"]["at"]   ← two levels of "data", then "at"

    BUG FIX: Original code had three .get("data") calls which produced an empty
    list every time because the third level doesn't exist.
    """

    parsed: List[Gstr1AdvanceEntry] = []

    # Correct path: payload → data → data → at
    at_entries = payload.get("data", {}).get("data", {}).get("at", [])

    for entry in at_entries:

        items: List[Gstr1AdvanceItem] = []

        for itm in entry.get("itms", []):
            items.append(
                Gstr1AdvanceItem(
                    advance_amount=itm.get("ad_amt", 0.0),
                    tax_rate=itm.get("rt", 0.0),
                    cgst=itm.get("camt", 0.0),
                    sgst=itm.get("samt", 0.0),
                    cess=itm.get("csamt", 0.0),
                )
            )

        parsed.append(
            Gstr1AdvanceEntry(
                place_of_supply=entry.get("pos", ""),
                supply_type=entry.get("sply_ty", ""),
                items=items,
            )
        )

    return parsed