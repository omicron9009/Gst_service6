from pydantic import BaseModel
from typing import List, Dict, Any


# -------------------------
# Shared request model
# -------------------------

class Gstr1RequestInfo(BaseModel):
    gstin: str
    year: str
    month: str
    endpoint: str


# -------------------------
# GSTR1 Advance Tax (AT)
# -------------------------

class Gstr1AdvanceItem(BaseModel):
    advance_amount: float
    tax_rate: float
    cgst: float
    sgst: float
    cess: float


class Gstr1AdvanceEntry(BaseModel):
    place_of_supply: str
    supply_type: str
    items: List[Gstr1AdvanceItem]


class Gstr1AdvanceTaxResponse(BaseModel):
    success: bool
    request: Gstr1RequestInfo
    upstream_status_code: int
    data: Dict[str, Any]


# # -------------------------
# # Future endpoints
# # -------------------------

# class Gstr1B2BResponse(BaseModel):
#     success: bool
#     request: Gstr1RequestInfo
#     upstream_status_code: int
#     data: Dict[str, Any]


# class Gstr1HSNResponse(BaseModel):
#     success: bool
#     request: Gstr1RequestInfo
#     upstream_status_code: int
#     data: Dict[str, Any]