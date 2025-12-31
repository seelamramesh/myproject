from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import Session, select, SQLModel
from contextlib import asynccontextmanager
from typing import List

from hotel_app.database import create_db_and_tables, get_session
from hotel_app.models import Customer, CustomerStatus, Table, TableStatus, MenuItem, Order, OrderItem
from hotel_app.services import create_tables, populate_menu, add_customer_to_queue, find_available_table

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    create_tables()
    populate_menu()
    yield

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="hotel_app/static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('hotel_app/static/index.html')

@app.post("/customers/join", response_model=Customer)
def join_queue(name: str, group_size: int, session: Session = Depends(get_session)):
    return add_customer_to_queue(name, group_size, session)

@app.get("/queue", response_model=List[Customer])
def get_queue(session: Session = Depends(get_session)):
    statement = select(Customer).where(Customer.status == CustomerStatus.WAITING).order_by(Customer.token)
    return session.exec(statement).all()

@app.get("/tables", response_model=List[Table])
def get_tables(session: Session = Depends(get_session)):
    return session.exec(select(Table)).all()

@app.post("/tables/assign")
def assign_tables(session: Session = Depends(get_session)):
    """
    Assigns tables to customers in the queue (FIFO).
    Iterates through waiting customers and tries to match them with available tables.
    """
    waiting_customers = session.exec(
        select(Customer)
        .where(Customer.status == CustomerStatus.WAITING)
        .order_by(Customer.token)
    ).all()

    assigned_count = 0

    for customer in waiting_customers:
        table = find_available_table(customer.group_size, session)
        if table:
            # Assign table
            table.status = TableStatus.OCCUPIED
            table.current_customer_id = customer.id
            customer.status = CustomerStatus.SEATED
            customer.assigned_table_id = table.id

            session.add(table)
            session.add(customer)
            session.commit() # Commit each assignment to update availability for next iteration
            assigned_count += 1

    return {"message": f"Assigned {assigned_count} customers to tables."}

class OrderItemCreate(SQLModel):
    menu_item_id: int
    quantity: int

class OrderCreate(SQLModel):
    items: List[OrderItemCreate]

@app.get("/menu", response_model=List[MenuItem])
def get_menu(session: Session = Depends(get_session)):
    return session.exec(select(MenuItem)).all()

@app.post("/orders/{table_id}", response_model=Order)
def place_order(table_id: int, order_create: OrderCreate, session: Session = Depends(get_session)):
    table = session.get(Table, table_id)
    if not table or table.status != TableStatus.OCCUPIED:
        raise HTTPException(status_code=400, detail="Table not occupied or does not exist")

    # Check if there's an open order for this table/customer
    # For simplicity, we create a new order or append to existing "OPEN" order
    # Here we will search for an existing OPEN order for this table
    existing_order = session.exec(
        select(Order).where(Order.table_id == table_id, Order.status == "OPEN")
    ).first()

    if existing_order:
        order = existing_order
    else:
        order = Order(
            table_id=table_id,
            customer_id=table.current_customer_id,
            status="OPEN"
        )
        session.add(order)
        session.commit()
        session.refresh(order)

    for item_data in order_create.items:
        menu_item = session.get(MenuItem, item_data.menu_item_id)
        if not menu_item:
            continue

        # Add to total amount
        order.total_amount += menu_item.price * item_data.quantity

        # Add order item
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity
        )
        session.add(order_item)

    session.add(order)
    session.commit()
    session.refresh(order)
    return order

@app.post("/billing/{table_id}/checkout")
def checkout(table_id: int, session: Session = Depends(get_session)):
    table = session.get(Table, table_id)
    if not table or table.status != TableStatus.OCCUPIED:
        raise HTTPException(status_code=400, detail="Table not occupied or does not exist")

    order = session.exec(
        select(Order).where(Order.table_id == table_id, Order.status == "OPEN")
    ).first()

    total_bill = 0.0
    if order:
        total_bill = order.total_amount
        order.status = "CLOSED"
        session.add(order)

    # Free the table
    customer_id = table.current_customer_id
    table.status = TableStatus.AVAILABLE
    table.current_customer_id = None
    session.add(table)

    # Update customer status
    if customer_id:
        customer = session.get(Customer, customer_id)
        if customer:
            customer.status = CustomerStatus.COMPLETED
            session.add(customer)

    session.commit()

    return {"message": "Checkout successful", "total_bill": total_bill}
