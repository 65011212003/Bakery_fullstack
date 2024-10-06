from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID, uuid4
import sqlite3
import os
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create a directory for storing images
if not os.path.exists("images"):
    os.makedirs("images")

app.mount("/images", StaticFiles(directory="images"), name="images")

# Initialize SQLite database
conn = sqlite3.connect('bakery.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        description TEXT,
        image_path TEXT
    )
''')
conn.commit()

class Item(BaseModel):
    id: Optional[UUID] = uuid4()
    name: str
    price: float
    description: Optional[str] = None
    image_path: Optional[str] = None

class UpdateItem(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None

@app.post("/items/", response_model=Item)
async def create_item(
    name: str = Form(...),
    price: float = Form(...),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    item_id = str(uuid4())
    image_path = None
    if image:
        file_extension = os.path.splitext(image.filename)[1]
        image_path = f"images/{item_id}{file_extension}"
        with open(image_path, "wb") as buffer:
            buffer.write(await image.read())
    
    cursor.execute('''
        INSERT INTO items (id, name, price, description, image_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (item_id, name, price, description, image_path))
    conn.commit()
    
    return Item(id=item_id, name=name, price=price, description=description, image_path=image_path)

@app.get("/items/", response_model=List[Item])
async def read_items():
    cursor.execute('SELECT * FROM items')
    items = cursor.fetchall()
    return [Item(id=UUID(item[0]), name=item[1], price=item[2], description=item[3], image_path=item[4]) for item in items]

@app.get("/items/{item_id}", response_model=Item)
async def read_item(item_id: UUID):
    cursor.execute('SELECT * FROM items WHERE id = ?', (str(item_id),))
    item = cursor.fetchone()
    if item:
        return Item(id=UUID(item[0]), name=item[1], price=item[2], description=item[3], image_path=item[4])
    raise HTTPException(status_code=404, detail="Item not found")

@app.put("/items/{item_id}", response_model=Item)
async def update_item(
    item_id: UUID,
    name: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    cursor.execute('SELECT * FROM items WHERE id = ?', (str(item_id),))
    existing_item = cursor.fetchone()
    if existing_item:
        update_fields = []
        update_values = []
        if name is not None:
            update_fields.append("name = ?")
            update_values.append(name)
        if price is not None:
            update_fields.append("price = ?")
            update_values.append(price)
        if description is not None:
            update_fields.append("description = ?")
            update_values.append(description)
        
        if image:
            file_extension = os.path.splitext(image.filename)[1]
            image_path = f"images/{item_id}{file_extension}"
            with open(image_path, "wb") as buffer:
                buffer.write(await image.read())
            update_fields.append("image_path = ?")
            update_values.append(image_path)
        
        if update_fields:
            update_query = f"UPDATE items SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(str(item_id))
            cursor.execute(update_query, update_values)
            conn.commit()
        
        cursor.execute('SELECT * FROM items WHERE id = ?', (str(item_id),))
        updated_item = cursor.fetchone()
        return Item(id=UUID(updated_item[0]), name=updated_item[1], price=updated_item[2], description=updated_item[3], image_path=updated_item[4])
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{item_id}")
async def delete_item(item_id: UUID):
    cursor.execute('DELETE FROM items WHERE id = ?', (str(item_id),))
    if cursor.rowcount > 0:
        conn.commit()
        return {"message": "Item deleted successfully"}
    raise HTTPException(status_code=404, detail="Item not found")
