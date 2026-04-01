import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
import logging

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DATABASE_PATH = os.getenv('DATABASE_PATH', './inventario.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'

db = SQLAlchemy(app)

# ============ MODELOS ============
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    vat_rate = db.Column(db.Float, default=0.19)
    current_stock = db.Column(db.Integer, default=0)
    initial_stock = db.Column(db.Integer, default=0)
    low_stock_threshold = db.Column(db.Integer, default=0)
    supplier_name = db.Column(db.String(255))
    total_sold = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def vat_amount(self):
        return self.price * self.vat_rate
    
    @property
    def price_with_vat(self):
        return self.price + self.vat_amount
    
    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'price': self.price,
            'vat_rate': self.vat_rate,
            'vat_amount': self.vat_amount,
            'price_with_vat': self.price_with_vat,
            'current_stock': self.current_stock,
            'initial_stock': self.initial_stock,
            'low_stock_threshold': self.low_stock_threshold,
            'supplier_name': self.supplier_name,
            'total_sold': self.total_sold,
        }

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    document_number = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(255))
    address = db.Column(db.String(500))

class InventoryMovement(db.Model):
    __tablename__ = 'inventory_movements'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity_change = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Purchase(db.Model):
    __tablename__ = 'purchases'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    total = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    total = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Remission(db.Model):
    __tablename__ = 'remissions'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    total = db.Column(db.Float, default=0)
    paid_amount = db.Column(db.Float, default=0)
    payment_notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Crear tablas
with app.app_context():
    db.create_all()

# ============ ENDPOINTS API ============

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        products = Product.query.all()
        return jsonify([p.to_dict() for p in products]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products', methods=['POST'])
def create_product():
    try:
        data = request.json
        if not data.get('name') or not data.get('sku'):
            return jsonify({'error': 'Nombre y SKU requeridos'}), 400
        if Product.query.filter_by(sku=data['sku']).first():
            return jsonify({'error': 'SKU ya existe'}), 400
        
        product = Product(
            sku=data['sku'],
            name=data['name'],
            price=float(data.get('price', 0)),
            vat_rate=float(data.get('vat_rate', 0.19)),
            current_stock=int(data.get('current_stock', 0)),
            initial_stock=int(data.get('current_stock', 0)),
            low_stock_threshold=int(data.get('low_stock_threshold', 0)),
            supplier_name=data.get('supplier_name', '')
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'message': 'Producto creado', 'product_id': product.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': 'No encontrado'}), 404
        data = request.json
        product.name = data.get('name', product.name)
        product.price = float(data.get('price', product.price))
        product.vat_rate = float(data.get('vat_rate', product.vat_rate))
        product.low_stock_threshold = int(data.get('low_stock_threshold', product.low_stock_threshold))
        product.current_stock = int(data.get('current_stock', product.current_stock))
        product.supplier_name = data.get('supplier_name', product.supplier_name)
        db.session.commit()
        return jsonify({'message': 'Actualizado'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': 'No encontrado'}), 404
        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': 'Eliminado'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/adjust', methods=['POST'])
def adjust_inventory():
    try:
        data = request.json
        product = Product.query.get(data['product_id'])
        if not product:
            return jsonify({'error': 'No encontrado'}), 404
        product.current_stock += int(data['quantity'])
        movement = InventoryMovement(
            product_id=product.id,
            quantity_change=int(data['quantity']),
            reason=data.get('reason', 'ajuste')
        )
        db.session.add(movement)
        db.session.commit()
        return jsonify({'message': f'Stock: {product.current_stock}'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/low-stock', methods=['GET'])
def get_alerts():
    try:
        products = Product.query.filter(Product.current_stock <= Product.low_stock_threshold).all()
        return jsonify([p.to_dict() for p in products]), 200
    except:
        return jsonify([]), 200

@app.route('/api/alerts/maintenance', methods=['GET'])
def get_maintenance():
    return jsonify([]), 200

@app.route('/api/products/search', methods=['GET'])
def search_products():
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify([]), 200
        products = Product.query.filter(
            (Product.name.ilike(f'%{query}%')) | (Product.sku.ilike(f'%{query}%'))
        ).limit(10).all()
        return jsonify([p.to_dict() for p in products]), 200
    except:
        return jsonify([]), 200

@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'No encontrado'}), 404

@app.errorhandler(500)
def error(e):
    db.session.rollback()
    return jsonify({'error': 'Error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
