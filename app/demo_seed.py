"""Repeat-safe example records for Phase 2 catalog tables.

The seed leaves product quantities at zero: Phase 3 introduces audited stock movements.
"""
from decimal import Decimal
from .extensions import db
from .models import Category, Supplier, Customer, Product

CATEGORY_NAMES = (
    "Electronics", "Food", "Clothing", "Furniture", "Beverages",
    "Office Supplies", "Accessories", "Cosmetics",
)

SUPPLIER_NAMES = (
    "Mekong Wholesale", "Angkor Electronics Supply", "Tonle Trading", "Khmer Stationery Co",
    "Phnom Penh Home Goods", "Lotus Beauty Wholesale", "Royal Garment Supply", "Golden River Imports",
    "Sokha Food Distribution", "Capital Beverage Co", "Blue Sky Accessories", "Green Field Products",
    "Bright Star Distribution", "Asia Tech Trading", "Sunrise Lifestyle Supply", "Smart Office Wholesale",
    "Lotus Home Furnishings", "Evergreen Consumer Goods", "Diamond Textile Supply", "Pacific Retail Partners",
)

CUSTOMER_NAMES = (
    "Dara Sok", "Sophea Chan", "Vanna Kim", "Sreymom Lim", "Rithy Heng",
    "Bopha Chea", "Piseth Long", "Sokly Pich", "Chenda Mao", "Vichea Noun",
    "Rachana Tea", "Sovann Ly", "Maly Touch", "Nita Sam", "Kosal Meas",
    "Lina Ouk", "Veasna Kong", "Rina Phan", "Borey Hak", "Sothea Yin",
)

# Name, category, cost, sale price, minimum quantity, unit, supplier index (0-19).
PRODUCTS = (
    ("Wireless Mouse", "Electronics", "8.50", "14.90", 5, "pcs", 1),
    ("USB-C Charging Cable", "Electronics", "2.80", "6.50", 10, "pcs", 13),
    ("Bluetooth Speaker", "Electronics", "18.00", "29.90", 3, "pcs", 1),
    ("Notebook A5", "Office Supplies", "1.20", "2.50", 15, "pcs", 3),
    ("Ballpoint Pen Pack", "Office Supplies", "1.80", "3.75", 10, "pack", 15),
    ("Desk Organizer", "Office Supplies", "5.00", "9.90", 5, "pcs", 3),
    ("Cotton T-Shirt", "Clothing", "4.50", "9.99", 8, "pcs", 6),
    ("Denim Jeans", "Clothing", "11.00", "21.50", 4, "pcs", 18),
    ("Canvas Backpack", "Accessories", "9.00", "18.00", 5, "pcs", 10),
    ("Sunglasses", "Accessories", "3.50", "8.90", 6, "pcs", 10),
    ("Green Tea 250g", "Food", "3.20", "5.90", 8, "pack", 8),
    ("Instant Noodles 5-Pack", "Food", "2.00", "3.80", 12, "pack", 8),
    ("Bottled Water 500ml", "Beverages", "0.25", "0.60", 30, "bottle", 9),
    ("Orange Juice 1L", "Beverages", "1.20", "2.50", 10, "bottle", 9),
    ("Wooden Chair", "Furniture", "22.00", "39.00", 2, "pcs", 16),
    ("Desk Lamp", "Furniture", "10.50", "19.90", 4, "pcs", 4),
    ("Hand Cream 100ml", "Cosmetics", "3.75", "7.50", 6, "pcs", 5),
    ("Face Cleanser 150ml", "Cosmetics", "6.00", "12.50", 5, "pcs", 5),
    ("Phone Stand", "Accessories", "2.25", "5.50", 8, "pcs", 7),
    ("Portable Power Bank", "Electronics", "13.00", "24.90", 4, "pcs", 13),
)


def seed_demo_records():
    """Insert up to 20 example products, suppliers and customers; skip existing keys."""
    counts = {"categories": 0, "suppliers": 0, "customers": 0, "products": 0}
    try:
        for name in CATEGORY_NAMES:
            if not Category.query.filter_by(name=name).first():
                db.session.add(Category(name=name, description=f"Sample {name.lower()} category"))
                counts["categories"] += 1
        db.session.flush()

        supplier_objects = []
        for i, name in enumerate(SUPPLIER_NAMES, 1):
            email = f"demo.supplier{i:02d}@example.com"
            supplier = Supplier.query.filter_by(email=email).first()
            if supplier is None:
                supplier = Supplier(
                    name=name, contact_person=f"Supplier Contact {i:02d}",
                    phone=f"+855 12 800 {i:03d}", email=email,
                    address="Phnom Penh, Cambodia", active=True,
                )
                db.session.add(supplier)
                counts["suppliers"] += 1
            supplier_objects.append(supplier)
        db.session.flush()

        for i, name in enumerate(CUSTOMER_NAMES, 1):
            email = f"demo.customer{i:02d}@example.com"
            if not Customer.query.filter_by(email=email).first():
                db.session.add(Customer(
                    name=name, phone=f"+855 17 600 {i:03d}", email=email,
                    address="Phnom Penh, Cambodia", active=True,
                ))
                counts["customers"] += 1
        db.session.flush()

        categories = {c.name: c for c in Category.query.filter(Category.name.in_(CATEGORY_NAMES)).all()}
        for i, (name, category_name, cost, price, minimum, unit, supplier_idx) in enumerate(PRODUCTS, 1):
            sku = f"DEMO-{i:03d}"
            if Product.query.filter_by(sku=sku).first():
                continue
            db.session.add(Product(
                name=name, sku=sku, barcode=f"890000000{i:03d}",
                category_id=categories[category_name].id,
                supplier_id=supplier_objects[supplier_idx].id,
                purchase_price=Decimal(cost), selling_price=Decimal(price),
                stock_quantity=0, minimum_stock=minimum, unit=unit,
                description="Example product for Phase 2 testing; not real inventory.",
                active=True,
            ))
            counts["products"] += 1
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return counts
