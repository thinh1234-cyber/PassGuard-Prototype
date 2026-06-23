from pydantic import BaseModel, Field
from typing import List
import uuid

class Account(BaseModel):
    username: str = ""
    password: str = ""

class Entry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    url: str = ""
    notes: str = ""
    accounts: List[Account] = Field(default_factory=list)

class Vault(BaseModel):
    entries: List[Entry] = []
