from sqlmodel import Session, select
from hotel_app.models import Table, MenuItem, Customer, CustomerStatus, TableStatus
from hotel_app.database import engine
from datetime import datetime

def create_tables():
    """Initializes the 50 tables with specified capacities."""
    with Session(engine) as session:
        # Check if tables already exist
        existing_tables = session.exec(select(Table)).first()
        if existing_tables:
            return

        tables = []
        # 20 tables of 2
        for _ in range(20):
            tables.append(Table(capacity=2))
        # 20 tables of 4
        for _ in range(20):
            tables.append(Table(capacity=4))
        # 10 tables of 6
        for _ in range(10):
            tables.append(Table(capacity=6))

        session.add_all(tables)
        session.commit()

def populate_menu():
    """Populates the Indian Veg Menu."""
    with Session(engine) as session:
        existing_menu = session.exec(select(MenuItem)).first()
        if existing_menu:
            return

        menu_items = [
            MenuItem(name="Paneer Butter Masala", category="Main Course", price=250.0, is_veg=True),
            MenuItem(name="Dal Makhani", category="Main Course", price=200.0, is_veg=True),
            MenuItem(name="Aloo Gobi", category="Main Course", price=180.0, is_veg=True),
            MenuItem(name="Vegetable Biryani", category="Main Course", price=220.0, is_veg=True),
            MenuItem(name="Naan", category="Breads", price=40.0, is_veg=True),
            MenuItem(name="Roti", category="Breads", price=30.0, is_veg=True),
            MenuItem(name="Samosa", category="Starters", price=50.0, is_veg=True),
            MenuItem(name="Paneer Tikka", category="Starters", price=280.0, is_veg=True),
            MenuItem(name="Gulab Jamun", category="Desserts", price=80.0, is_veg=True),
            MenuItem(name="Rasmalai", category="Desserts", price=90.0, is_veg=True),
            MenuItem(name="Masala Chai", category="Beverages", price=30.0, is_veg=True),
            MenuItem(name="Lassi", category="Beverages", price=60.0, is_veg=True),
        ]
        session.add_all(menu_items)
        session.commit()

def find_available_table(group_size: int, session: Session) -> Table | None:
    """Finds an available table suitable for the group size."""
    # Find tables with capacity >= group_size and status AVAILABLE
    # Sort by capacity asc to assign best fit
    statement = select(Table).where(
        Table.capacity >= group_size,
        Table.status == TableStatus.AVAILABLE
    ).order_by(Table.capacity)

    return session.exec(statement).first()

def add_customer_to_queue(name: str, group_size: int, session: Session) -> Customer:
    """Adds a customer to the waiting queue."""
    # Generate token (simple increment or random, here simple max(token) + 1)
    last_token = session.exec(select(Customer.token).order_by(Customer.token.desc())).first()
    new_token = (last_token or 0) + 1

    customer = Customer(
        name=name,
        group_size=group_size,
        token=new_token,
        status=CustomerStatus.WAITING,
        arrival_time=datetime.now()
    )
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer
