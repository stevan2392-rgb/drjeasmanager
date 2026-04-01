import csv
import io
import os
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, or_

load_dotenv()


def utcnow():
    return datetime.utcnow()


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "inventario.db")
DATABASE_PATH = os.path.abspath(os.getenv("DATABASE_PATH", DEFAULT_DB_PATH))
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
SQLITE_URI_PATH = Path(DATABASE_PATH).as_posix()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{SQLITE_URI_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JSON_SORT_KEYS"] = False

db = SQLAlchemy(app)


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Product(TimestampMixin, db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    current_stock = db.Column(db.Integer, nullable=False, default=0)
    initial_stock = db.Column(db.Integer, nullable=False, default=0)
    low_stock_threshold = db.Column(db.Integer, nullable=False, default=0)
    supplier_name = db.Column(db.String(255), default="")
    total_sold = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "price": self.price,
            "current_stock": self.current_stock,
            "initial_stock": self.initial_stock,
            "low_stock_threshold": self.low_stock_threshold,
            "supplier_name": self.supplier_name or "",
            "total_sold": self.total_sold,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Customer(TimestampMixin, db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    document_number = db.Column(db.String(50), index=True)
    phone = db.Column(db.String(50), default="")
    email = db.Column(db.String(255), default="")
    address = db.Column(db.String(500), default="")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "document_number": self.document_number or "",
            "phone": self.phone or "",
            "email": self.email or "",
            "address": self.address or "",
        }


class InventoryMovement(TimestampMixin, db.Model):
    __tablename__ = "inventory_movements"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity_change = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), default="ajuste")

    product = db.relationship("Product")


class Purchase(TimestampMixin, db.Model):
    __tablename__ = "purchases"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    supplier_name = db.Column(db.String(255), default="")
    supplier_phone = db.Column(db.String(50), default="")
    supplier_email = db.Column(db.String(255), default="")
    supplier_address = db.Column(db.String(500), default="")
    subtotal = db.Column(db.Float, nullable=False, default=0)
    total = db.Column(db.Float, nullable=False, default=0)
    notes = db.Column(db.Text, default="")

    items = db.relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

    def to_dict(self, include_items=False):
        payload = {
            "id": self.id,
            "code": self.code,
            "date": self.created_at.isoformat(),
            "supplier": {
                "name": self.supplier_name or "",
                "phone": self.supplier_phone or "",
                "email": self.supplier_email or "",
                "address": self.supplier_address or "",
            },
            "subtotal": self.subtotal,
            "total": self.total,
            "notes": self.notes or "",
        }
        if include_items:
            payload["items"] = [item.to_dict() for item in self.items]
        return payload


class PurchaseItem(db.Model):
    __tablename__ = "purchase_items"

    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey("purchases.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    unit_cost = db.Column(db.Float, nullable=False, default=0)
    line_total = db.Column(db.Float, nullable=False, default=0)

    purchase = db.relationship("Purchase", back_populates="items")
    product = db.relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "unit_cost": self.unit_cost,
            "line_total": self.line_total,
            "product": self.product.to_dict() if self.product else None,
        }


class Invoice(TimestampMixin, db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    subtotal = db.Column(db.Float, nullable=False, default=0)
    total = db.Column(db.Float, nullable=False, default=0)
    payment_method = db.Column(db.String(100), default="EFECTIVO")
    notes = db.Column(db.Text, default="")

    customer = db.relationship("Customer")
    items = db.relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

    def to_dict(self, include_items=False):
        payload = {
            "id": self.id,
            "number": self.number,
            "date": self.created_at.isoformat(),
            "customer": self.customer.to_dict() if self.customer else None,
            "subtotal": self.subtotal,
            "total": self.total,
            "payment_method": self.payment_method or "EFECTIVO",
            "notes": self.notes or "",
        }
        if include_items:
            payload["items"] = [item.to_dict() for item in self.items]
        return payload


class InvoiceItem(db.Model):
    __tablename__ = "invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    unit_price = db.Column(db.Float, nullable=False, default=0)
    line_total = db.Column(db.Float, nullable=False, default=0)

    invoice = db.relationship("Invoice", back_populates="items")
    product = db.relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "line_total": self.line_total,
            "product": self.product.to_dict() if self.product else None,
        }


class Remission(TimestampMixin, db.Model):
    __tablename__ = "remissions"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    subtotal = db.Column(db.Float, nullable=False, default=0)
    total = db.Column(db.Float, nullable=False, default=0)
    paid_amount = db.Column(db.Float, nullable=False, default=0)
    payment_method = db.Column(db.String(100), default="EFECTIVO")
    payment_notes = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")
    status = db.Column(db.String(50), default="pendiente")

    customer = db.relationship("Customer")
    items = db.relationship("RemissionItem", back_populates="remission", cascade="all, delete-orphan")

    @property
    def balance_due(self):
        return max(float(self.total or 0) - float(self.paid_amount or 0), 0)

    def to_dict(self, include_items=False):
        payload = {
            "id": self.id,
            "number": self.number,
            "date": self.created_at.isoformat(),
            "customer": self.customer.to_dict() if self.customer else None,
            "subtotal": self.subtotal,
            "total": self.total,
            "paid_amount": self.paid_amount,
            "balance_due": self.balance_due,
            "payment_method": self.payment_method or "EFECTIVO",
            "payment_notes": self.payment_notes or "",
            "notes": self.notes or "",
            "status": self.status or "pendiente",
        }
        if include_items:
            payload["items"] = [item.to_dict() for item in self.items]
        return payload


class RemissionItem(db.Model):
    __tablename__ = "remission_items"

    id = db.Column(db.Integer, primary_key=True)
    remission_id = db.Column(db.Integer, db.ForeignKey("remissions.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    unit_price = db.Column(db.Float, nullable=False, default=0)
    line_total = db.Column(db.Float, nullable=False, default=0)

    remission = db.relationship("Remission", back_populates="items")
    product = db.relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "line_total": self.line_total,
            "product": self.product.to_dict() if self.product else None,
        }


class MaintenanceReminder(TimestampMixin, db.Model):
    __tablename__ = "maintenance_reminders"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    due_date = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text, default="")
    completed = db.Column(db.Boolean, nullable=False, default=False)

    customer = db.relationship("Customer")

    def to_dict(self):
        return {
            "id": self.id,
            "due_date": self.due_date.date().isoformat() if self.due_date else None,
            "notes": self.notes or "",
            "customer": self.customer.to_dict() if self.customer else None,
        }


def sqlite_columns(table_name):
    rows = db.session.execute(db.text(f"PRAGMA table_info({table_name})")).fetchall()
    return {row[1] for row in rows}


def ensure_column(table_name, column_name, sql_definition):
    if column_name not in sqlite_columns(table_name):
        db.session.execute(db.text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_definition}"))
        db.session.commit()


def run_migrations():
    db.create_all()
    table_names = set(inspect(db.engine).get_table_names())

    if "products" in table_names:
        ensure_column("products", "price", "FLOAT NOT NULL DEFAULT 0")
        ensure_column("products", "current_stock", "INTEGER NOT NULL DEFAULT 0")
        ensure_column("products", "initial_stock", "INTEGER NOT NULL DEFAULT 0")
        ensure_column("products", "low_stock_threshold", "INTEGER NOT NULL DEFAULT 0")
        ensure_column("products", "supplier_name", "VARCHAR(255) DEFAULT ''")
        ensure_column("products", "total_sold", "INTEGER NOT NULL DEFAULT 0")
        ensure_column("products", "created_at", "DATETIME")
        ensure_column("products", "updated_at", "DATETIME")

    for table_name, definitions in {
        "customers": {
            "document_number": "VARCHAR(50)",
            "phone": "VARCHAR(50) DEFAULT ''",
            "email": "VARCHAR(255) DEFAULT ''",
            "address": "VARCHAR(500) DEFAULT ''",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
        "purchases": {
            "supplier_name": "VARCHAR(255) DEFAULT ''",
            "supplier_phone": "VARCHAR(50) DEFAULT ''",
            "supplier_email": "VARCHAR(255) DEFAULT ''",
            "supplier_address": "VARCHAR(500) DEFAULT ''",
            "subtotal": "FLOAT NOT NULL DEFAULT 0",
            "total": "FLOAT NOT NULL DEFAULT 0",
            "notes": "TEXT DEFAULT ''",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
        "invoices": {
            "subtotal": "FLOAT NOT NULL DEFAULT 0",
            "total": "FLOAT NOT NULL DEFAULT 0",
            "payment_method": "VARCHAR(100) DEFAULT 'EFECTIVO'",
            "notes": "TEXT DEFAULT ''",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
        "remissions": {
            "subtotal": "FLOAT NOT NULL DEFAULT 0",
            "total": "FLOAT NOT NULL DEFAULT 0",
            "paid_amount": "FLOAT NOT NULL DEFAULT 0",
            "payment_method": "VARCHAR(100) DEFAULT 'EFECTIVO'",
            "payment_notes": "TEXT DEFAULT ''",
            "notes": "TEXT DEFAULT ''",
            "status": "VARCHAR(50) DEFAULT 'pendiente'",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
        "inventory_movements": {
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
    }.items():
        if table_name in table_names:
            for column_name, definition in definitions.items():
                ensure_column(table_name, column_name, definition)


def next_code(prefix, model, field_name):
    latest = model.query.order_by(model.id.desc()).first()
    next_number = 1
    if latest:
        current_value = getattr(latest, field_name, "") or ""
        digits = "".join(ch for ch in current_value if ch.isdigit())
        if digits:
            next_number = int(digits) + 1
    return f"{prefix}-{next_number:05d}"


def parse_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_float(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_text(value):
    return (value or "").strip()


def get_or_create_customer(payload):
    payload = payload or {}
    name = normalize_text(payload.get("name"))
    if not name:
        raise ValueError("El nombre del cliente es obligatorio")

    document_number = normalize_text(payload.get("document_number"))
    email = normalize_text(payload.get("email"))
    phone = normalize_text(payload.get("phone"))
    address = normalize_text(payload.get("address"))

    customer = None
    if document_number:
        customer = Customer.query.filter_by(document_number=document_number).first()
    if not customer and email:
        customer = Customer.query.filter_by(email=email).first()
    if not customer and phone:
        customer = Customer.query.filter_by(phone=phone).first()
    if not customer:
        customer = Customer(name=name)
        db.session.add(customer)

    customer.name = name
    customer.document_number = document_number
    customer.email = email
    customer.phone = phone
    customer.address = address
    return customer


def movement_reason(prefix, reference):
    return f"{prefix} {reference}".strip()


def validate_product_payload(data, product=None):
    name = normalize_text(data.get("name"))
    sku = normalize_text(data.get("sku")) if "sku" in data or not product else product.sku
    if not name:
        raise ValueError("El nombre del producto es obligatorio")
    if not sku:
        raise ValueError("El SKU es obligatorio")

    existing = Product.query.filter(Product.sku == sku)
    if product:
        existing = existing.filter(Product.id != product.id)
    if existing.first():
        raise ValueError("Ya existe un producto con ese SKU")

    return {
        "name": name,
        "sku": sku,
        "price": max(parse_float(data.get("price"), product.price if product else 0), 0),
        "low_stock_threshold": max(parse_int(data.get("low_stock_threshold"), product.low_stock_threshold if product else 0), 0),
        "current_stock": max(parse_int(data.get("current_stock"), product.current_stock if product else 0), 0),
        "supplier_name": normalize_text(data.get("supplier_name")) if "supplier_name" in data else (product.supplier_name if product else ""),
    }


def serialize_items_display(items):
    return [
        {
            "index": index,
            "product": item.product,
            "quantity": item.quantity,
            "unit_price": getattr(item, "unit_price", getattr(item, "unit_cost", 0)),
            "total": item.line_total,
        }
        for index, item in enumerate(items, start=1)
    ]


def number_to_words_es(number):
    units = ("", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve")
    teens = ("diez", "once", "doce", "trece", "catorce", "quince", "dieciseis", "diecisiete", "dieciocho", "diecinueve")
    tens = ("", "", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa")
    hundreds = ("", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos")

    def convert_hundreds(n):
        if n == 0:
            return ""
        if n == 100:
            return "cien"
        if n < 10:
            return units[n]
        if n < 20:
            return teens[n - 10]
        if n < 30:
            return "veinte" if n == 20 else "veinti" + units[n - 20]
        if n < 100:
            ten = n // 10
            unit = n % 10
            return tens[ten] if unit == 0 else f"{tens[ten]} y {units[unit]}"
        hundred = n // 100
        rest = n % 100
        return hundreds[hundred] if rest == 0 else f"{hundreds[hundred]} {convert_hundreds(rest)}"

    def convert(n):
        if n == 0:
            return "cero"
        if n < 1000:
            return convert_hundreds(n)
        if n < 1_000_000:
            thousands = n // 1000
            rest = n % 1000
            prefix = "mil" if thousands == 1 else f"{convert_hundreds(thousands)} mil"
            return prefix if rest == 0 else f"{prefix} {convert_hundreds(rest)}"
        millions = n // 1_000_000
        rest = n % 1_000_000
        prefix = "un millon" if millions == 1 else f"{convert(millions)} millones"
        return prefix if rest == 0 else f"{prefix} {convert(rest)}"

    return convert(int(round(number or 0))).upper() + " PESOS M/L"


def sale_report_rows():
    rows = []
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    remissions = Remission.query.order_by(Remission.created_at.desc()).all()

    for invoice in invoices:
        for item in invoice.items:
            rows.append(
                {
                    "tipo": "Factura",
                    "numero": invoice.number,
                    "fecha": invoice.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "cliente": invoice.customer.name if invoice.customer else "",
                    "documento": invoice.customer.document_number if invoice.customer else "",
                    "producto": item.product.name if item.product else "",
                    "sku": item.product.sku if item.product else "",
                    "cantidad": item.quantity,
                    "valor_unitario": item.unit_price,
                    "total_linea": item.line_total,
                    "total_documento": invoice.total,
                    "abono": "",
                    "saldo": "",
                    "estado": "",
                }
            )
    for remission in remissions:
        for item in remission.items:
            rows.append(
                {
                    "tipo": "Remision",
                    "numero": remission.number,
                    "fecha": remission.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "cliente": remission.customer.name if remission.customer else "",
                    "documento": remission.customer.document_number if remission.customer else "",
                    "producto": item.product.name if item.product else "",
                    "sku": item.product.sku if item.product else "",
                    "cantidad": item.quantity,
                    "valor_unitario": item.unit_price,
                    "total_linea": item.line_total,
                    "total_documento": remission.total,
                    "abono": remission.paid_amount,
                    "saldo": remission.balance_due,
                    "estado": remission.status,
                }
            )
    return rows


@app.route("/static/<path:path>")
def send_static(path):
    return send_from_directory(app.static_folder, path)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/history/purchases")
def purchases_history():
    return render_template("purchases_history.html")


@app.route("/history/invoices")
def invoices_history():
    return render_template("invoices_history.html")


@app.route("/history/remissions")
def remissions_history():
    return render_template("remissions_history.html")


@app.route("/invoice/<int:invoice_id>")
def invoice_view(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template(
        "invoice.html",
        invoice=invoice,
        invoice_items_display=serialize_items_display(invoice.items),
        items_fillers=max(0, 8 - len(invoice.items)),
        total_to_pay=invoice.total,
        total_en_letras=number_to_words_es(invoice.total),
    )


@app.route("/invoice/<int:invoice_id>/pdf")
def invoice_pdf(invoice_id):
    return invoice_view(invoice_id)


@app.route("/remission/<int:remission_id>")
def remission_view(remission_id):
    remission = Remission.query.get_or_404(remission_id)
    return render_template(
        "remission.html",
        remission=remission,
        remission_items_display=serialize_items_display(remission.items),
        items_fillers=max(0, 8 - len(remission.items)),
        total_to_pay=remission.total,
        total_en_letras=number_to_words_es(remission.total),
    )


@app.route("/remission/<int:remission_id>/pdf")
def remission_pdf(remission_id):
    return remission_view(remission_id)


@app.route("/api/products", methods=["GET"])
def get_products():
    products = Product.query.order_by(Product.name.asc()).all()
    return jsonify([product.to_dict() for product in products]), 200


@app.route("/api/products/search", methods=["GET"])
def search_products():
    query = normalize_text(request.args.get("q"))
    if len(query) < 2:
        return jsonify([]), 200
    products = (
        Product.query.filter(or_(Product.name.ilike(f"%{query}%"), Product.sku.ilike(f"%{query}%")))
        .order_by(Product.name.asc())
        .limit(20)
        .all()
    )
    return jsonify([product.to_dict() for product in products]), 200


@app.route("/api/products", methods=["POST"])
def create_product():
    try:
        data = request.get_json(force=True) or {}
        payload = validate_product_payload(data)
        product = Product(**payload)
        db.session.add(product)
        db.session.flush()
        if product.current_stock:
            db.session.add(
                InventoryMovement(
                    product_id=product.id,
                    quantity_change=product.current_stock,
                    reason="stock inicial",
                )
            )
        db.session.commit()
        return jsonify({"message": "Producto creado", "product": product.to_dict()}), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        data = request.get_json(force=True) or {}
        previous_stock = product.current_stock
        payload = validate_product_payload(data, product=product)
        product.sku = payload["sku"]
        product.name = payload["name"]
        product.price = payload["price"]
        product.low_stock_threshold = payload["low_stock_threshold"]
        product.supplier_name = payload["supplier_name"]
        product.current_stock = payload["current_stock"]

        stock_delta = product.current_stock - previous_stock
        if stock_delta:
            db.session.add(
                InventoryMovement(
                    product_id=product.id,
                    quantity_change=stock_delta,
                    reason=normalize_text(data.get("reason")) or "edicion de producto",
                )
            )
        db.session.commit()
        return jsonify({"message": "Producto actualizado", "product": product.to_dict()}), 200
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    has_usage = any(
        [
            PurchaseItem.query.filter_by(product_id=product.id).first(),
            InvoiceItem.query.filter_by(product_id=product.id).first(),
            RemissionItem.query.filter_by(product_id=product.id).first(),
            InventoryMovement.query.filter_by(product_id=product.id).first(),
        ]
    )
    if has_usage:
        return jsonify({"error": "No se puede eliminar porque el producto ya tiene movimientos o ventas registradas"}), 400
    try:
        db.session.delete(product)
        db.session.commit()
        return jsonify({"message": "Producto eliminado"}), 200
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@app.route("/api/inventory/adjust", methods=["POST"])
def adjust_inventory():
    data = request.get_json(force=True) or {}
    product = Product.query.get_or_404(parse_int(data.get("product_id")))
    quantity = parse_int(data.get("quantity"))
    if quantity == 0:
        return jsonify({"error": "La cantidad no puede ser 0"}), 400
    if product.current_stock + quantity < 0:
        return jsonify({"error": "No hay stock suficiente para realizar ese ajuste"}), 400
    try:
        product.current_stock += quantity
        db.session.add(
            InventoryMovement(
                product_id=product.id,
                quantity_change=quantity,
                reason=normalize_text(data.get("reason")) or "ajuste manual",
            )
        )
        db.session.commit()
        return jsonify({"message": "Inventario actualizado", "current_stock": product.current_stock}), 200
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@app.route("/api/alerts/low-stock", methods=["GET"])
def low_stock_alerts():
    products = (
        Product.query.filter(Product.low_stock_threshold > 0, Product.current_stock <= Product.low_stock_threshold)
        .order_by(Product.current_stock.asc(), Product.name.asc())
        .all()
    )
    return jsonify([product.to_dict() for product in products]), 200


@app.route("/api/alerts/maintenance", methods=["GET"])
def maintenance_alerts():
    today = datetime.utcnow()
    upcoming = today + timedelta(days=14)
    reminders = (
        MaintenanceReminder.query.filter(
            MaintenanceReminder.completed.is_(False),
            MaintenanceReminder.due_date >= today,
            MaintenanceReminder.due_date <= upcoming,
        )
        .order_by(MaintenanceReminder.due_date.asc())
        .all()
    )
    return jsonify([reminder.to_dict() for reminder in reminders]), 200


@app.route("/api/alerts/maintenance/complete", methods=["POST"])
def complete_maintenance():
    data = request.get_json(force=True) or {}
    reminder = MaintenanceReminder.query.get_or_404(parse_int(data.get("id")))
    reminder.completed = True
    db.session.commit()
    return jsonify({"message": "Mantenimiento marcado como realizado"}), 200


@app.route("/api/purchases", methods=["POST"])
def create_purchase():
    data = request.get_json(force=True) or {}
    items = data.get("items") or []
    if not items:
        return jsonify({"error": "Debes agregar al menos un item"}), 400
    try:
        purchase = Purchase(
            code=next_code("COMP", Purchase, "code"),
            supplier_name=normalize_text((data.get("supplier") or {}).get("name")),
            supplier_phone=normalize_text((data.get("supplier") or {}).get("phone")),
            supplier_email=normalize_text((data.get("supplier") or {}).get("email")),
            supplier_address=normalize_text((data.get("supplier") or {}).get("address")),
            notes=normalize_text(data.get("notes")),
        )
        db.session.add(purchase)
        db.session.flush()

        total = 0
        for item in items:
            product = Product.query.get_or_404(parse_int(item.get("product_id")))
            quantity = parse_int(item.get("quantity"))
            unit_cost = max(parse_float(item.get("unit_cost")), 0)
            if quantity <= 0:
                raise ValueError("Todas las cantidades deben ser mayores a 0")
            line_total = round(quantity * unit_cost, 2)
            total += line_total
            product.current_stock += quantity

            db.session.add(
                PurchaseItem(
                    purchase_id=purchase.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_cost=unit_cost,
                    line_total=line_total,
                )
            )
            db.session.add(
                InventoryMovement(
                    product_id=product.id,
                    quantity_change=quantity,
                    reason=movement_reason("compra", purchase.code),
                )
            )

        purchase.subtotal = round(total, 2)
        purchase.total = round(total, 2)
        db.session.commit()
        return jsonify({"id": purchase.id, "code": purchase.code, "total": purchase.total}), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@app.route("/api/purchases/history", methods=["GET"])
def purchases_history_api():
    purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    return jsonify([purchase.to_dict(include_items=False) for purchase in purchases]), 200


@app.route("/api/purchases/<int:purchase_id>", methods=["GET"])
def purchase_detail_api(purchase_id):
    purchase = Purchase.query.get_or_404(purchase_id)
    return jsonify(purchase.to_dict(include_items=True)), 200


def create_sale_document(model, item_model, prefix):
    data = request.get_json(force=True) or {}
    items = data.get("items") or []
    if not items:
        return jsonify({"error": "Debes agregar al menos un item"}), 400

    try:
        customer = get_or_create_customer(data.get("customer"))
        db.session.flush()
        document = model(
            number=next_code(prefix, model, "number"),
            customer_id=customer.id,
            payment_method=normalize_text(data.get("payment_method")) or "EFECTIVO",
            notes=normalize_text(data.get("notes")),
        )
        if isinstance(document, Remission):
            document.paid_amount = max(parse_float(data.get("paid_amount")), 0)
            document.payment_notes = normalize_text(data.get("payment_notes"))

        db.session.add(document)
        db.session.flush()

        subtotal = 0
        total_quantity = 0
        foreign_key_name = f"{document.__tablename__[:-1]}_id"
        for item in items:
            product = Product.query.get_or_404(parse_int(item.get("product_id")))
            quantity = parse_int(item.get("quantity"))
            unit_price = max(parse_float(item.get("unit_price"), product.price), 0)
            if quantity <= 0:
                raise ValueError("Todas las cantidades deben ser mayores a 0")
            if product.current_stock < quantity:
                raise ValueError(f"No hay suficiente stock para {product.name}")

            line_total = round(quantity * unit_price, 2)
            subtotal += line_total
            total_quantity += quantity
            product.current_stock -= quantity
            product.total_sold += quantity

            db.session.add(
                item_model(
                    **{
                        foreign_key_name: document.id,
                        "product_id": product.id,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "line_total": line_total,
                    }
                )
            )
            db.session.add(
                InventoryMovement(
                    product_id=product.id,
                    quantity_change=-quantity,
                    reason=movement_reason(document.number.lower(), document.number),
                )
            )

        document.subtotal = round(subtotal, 2)
        document.total = round(subtotal, 2)
        if isinstance(document, Remission):
            if document.paid_amount > document.total:
                raise ValueError("El abono no puede superar el total de la remision")
            document.status = "cancelado" if document.balance_due == 0 else "pendiente"

        maintenance_days = parse_int(data.get("maintenance_days"))
        if maintenance_days > 0:
            db.session.add(
                MaintenanceReminder(
                    customer_id=customer.id,
                    due_date=datetime.utcnow() + timedelta(days=maintenance_days),
                    notes=f"Control por venta {document.number}",
                )
            )

        db.session.commit()
        return jsonify({"id": document.id, "number": document.number, "total": document.total, "items": total_quantity}), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@app.route("/api/invoices", methods=["POST"])
def create_invoice():
    return create_sale_document(Invoice, InvoiceItem, "FAC")


@app.route("/api/remissions", methods=["POST"])
def create_remission():
    return create_sale_document(Remission, RemissionItem, "REM")


@app.route("/api/invoices/history", methods=["GET"])
def invoices_history_api():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return jsonify([invoice.to_dict(include_items=False) for invoice in invoices]), 200


@app.route("/api/remissions/history", methods=["GET"])
def remissions_history_api():
    remissions = Remission.query.order_by(Remission.created_at.desc()).all()
    return jsonify([remission.to_dict(include_items=False) for remission in remissions]), 200


@app.route("/api/customers/search", methods=["GET"])
def search_customers():
    query = normalize_text(request.args.get("q"))
    if len(query) < 2:
        return jsonify([]), 200
    customers = (
        Customer.query.filter(
            or_(
                Customer.name.ilike(f"%{query}%"),
                Customer.document_number.ilike(f"%{query}%"),
                Customer.phone.ilike(f"%{query}%"),
            )
        )
        .order_by(Customer.name.asc())
        .limit(15)
        .all()
    )
    return jsonify([customer.to_dict() for customer in customers]), 200


@app.route("/api/reports/sales", methods=["GET"])
def sales_report_api():
    rows = sale_report_rows()
    fmt = normalize_text(request.args.get("format")).lower()
    if fmt == "csv":
        buffer = io.StringIO()
        fieldnames = [
            "tipo",
            "numero",
            "fecha",
            "cliente",
            "documento",
            "producto",
            "sku",
            "cantidad",
            "valor_unitario",
            "total_linea",
            "total_documento",
            "abono",
            "saldo",
            "estado",
        ]
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        filename = f"reporte_ventas_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            buffer.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    total_sales = round(sum(row["total_linea"] for row in rows), 2)
    return jsonify({"rows": rows, "summary": {"records": len(rows), "total_sales": total_sales}}), 200


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "No encontrado"}), 404
    return "No encontrado", 404


@app.errorhandler(500)
def internal_error(_error):
    db.session.rollback()
    return jsonify({"error": "Error interno del servidor"}), 500


with app.app_context():
    run_migrations()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
