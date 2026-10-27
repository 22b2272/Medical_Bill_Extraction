from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BillItem(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    item_name: str = Field(min_length=1)
    item_amount: float
    item_rate: float
    item_quantity: float


class PagewiseLineItems(BaseModel):
    page_no: int = Field(ge=1)
    page_type: Literal["Bill Detail", "Final Bill", "Pharmacy"]
    bill_items: list[BillItem]
    validation_warnings: list[str] = Field(default_factory=list)


class TokenUsage(BaseModel):
    total_tokens: int
    input_tokens: int
    output_tokens: int


class BillData(BaseModel):
    pagewise_line_items: list[PagewiseLineItems]
    total_item_count: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)


class BillExtractionResponse(BaseModel):
    is_success: bool
    token_usage: TokenUsage
    data: BillData


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
