from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    initial_stock = Column(Integer, nullable=False)
    current_stock = Column(Integer, nullable=False)
    low_stock_threshold = Column(Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'initial_stock': self.initial_stock,
            'current_stock': self.current_stock,
            'low_stock_threshold': self.low_stock_threshold
        }

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone
        }

class Purchase(Base):
    __tablename__ = 'purchases'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    purchase_date = Column(String)  # You might want to use Date or DateTime type

    product = relationship('Product')
    customer = relationship('Customer')

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'customer_id': self.customer_id,
            'quantity': self.quantity,
            'purchase_date': self.purchase_date
        }

class Invoice(Base):
    __tablename__ = 'invoices'
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0)
    payment_notes = Column(String)
    invoice_date = Column(String)  # You might want to use Date or DateTime type

    customer = relationship('Customer')

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'total_amount': self.total_amount,
            'paid_amount': self.paid_amount,
            'payment_notes': self.payment_notes,
            'invoice_date': self.invoice_date
        }

class Remission(Base):
    __tablename__ = 'remissions'
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False)
    remission_date = Column(String)  # You might want to use Date or DateTime type
    amount = Column(Float, nullable=False)

    invoice = relationship('Invoice')

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'remission_date': self.remission_date,
            'amount': self.amount
        }