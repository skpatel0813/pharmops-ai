from pydantic import BaseModel
from typing import Optional


class StatusUpdate(BaseModel):
    status: str
    pharmacist_note: Optional[str] = None


class MedRecUpdate(BaseModel):
    status: str
    pharmacist_note: Optional[str] = None