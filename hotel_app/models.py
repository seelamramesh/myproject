from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class TableStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"

class CustomerStatus(str, Enum):
    WAITING = "WAITING"
    SEATED = "SEATED"
    COMPLETED = "COMPLETED"

class Table(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    capacity: int
    status: TableStatus = Field(default=TableStatus.AVAILABLE)
    current_customer_id: Optional[int] = Field(default=None) # Logic handled in service, no direct foreign key to avoid circular deps if not needed

class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    group_size: int
    token: int
    status: CustomerStatus = Field(default=CustomerStatus.WAITING)
    arrival_time: datetime = Field(default_factory=datetime.now)
    assigned_table_id: Optional[int] = Field(default=None)

class MenuItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    category: str
    price: float
    is_veg: bool = Field(default=True)

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    table_id: int = Field(foreign_key="table.id")
    customer_id: int = Field(foreign_key="customer.id")
    total_amount: float = 0.0
    status: str = "OPEN" # OPEN, CLOSED

    items: List["OrderItem"] = Relationship(back_populates="order")

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    menu_item_id: int = Field(foreign_key="menuitem.id")
    quantity: int = 1

    order: Optional[Order] = Relationship(back_populates="items")
