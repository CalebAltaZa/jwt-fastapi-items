"""Pydantic schemas of the API."""

from typing import Optional

from pydantic import BaseModel, Field

from .config import CATEGORIES


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120, examples=["Avengers: Doomsday"])
    category: str = Field(default="Otros", examples=["Películas"])
    image_url: Optional[str] = Field(default=None, max_length=500)
    note: Optional[str] = Field(default=None, max_length=500)

    def normalized(self) -> dict:
        category = self.category if self.category in CATEGORIES else "Otros"
        return {
            "name": self.name.strip(),
            "category": category,
            "image_url": (self.image_url or "").strip() or None,
            "note": (self.note or "").strip() or None,
        }


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    category: Optional[str] = None
    image_url: Optional[str] = Field(default=None, max_length=500)
    note: Optional[str] = Field(default=None, max_length=500)
    favorite: Optional[bool] = None


class Item(BaseModel):
    id: int
    username: str
    name: str
    category: str
    image_url: Optional[str] = None
    note: Optional[str] = None
    favorite: bool
    created_at: str
