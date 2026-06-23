from pydantic import BaseModel, Field
from typing import List
import uuid

class Entry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    username: str
    password: str
    url: str = ""
    notes: str = ""

class Vault(BaseModel):
    entries: List[Entry] = []
