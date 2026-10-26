"""Small in-memory CRUD service for the DDIA homework."""

from threading import Lock

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


class ItemInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


class Item(ItemInput):
    id: int


app = FastAPI(
    title="DDIA Items",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

_items: dict[int, Item] = {}
_next_id = 1
_lock = Lock()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemInput) -> Item:
    global _next_id
    with _lock:
        item = Item(id=_next_id, **payload.model_dump())
        _items[_next_id] = item
        _next_id += 1
    return item


@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int) -> Item:
    with _lock:
        item = _items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, payload: ItemInput) -> Item:
    with _lock:
        if item_id not in _items:
            raise HTTPException(status_code=404, detail="Item not found")
        item = Item(id=item_id, **payload.model_dump())
        _items[item_id] = item
    return item
