from flask import Flask, request, jsonify
from models import Product, Customer, Remission, db  # Assuming these models are defined

app = Flask(__name__)

# 1) PUT endpoint to update products
@app.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.json
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    try:
        product.name = data.get('name', product.name)
        product.price = data.get('price', product.price)
        product.vat_rate = data.get('vat_rate', product.vat_rate)
        product.low_stock_threshold = data.get('low_stock_threshold', product.low_stock_threshold)
        product.current_stock = data.get('current_stock', product.current_stock)
        db.session.commit()  # Commit transaction
        return jsonify({'message': 'Product updated successfully'}), 200
    except Exception as e:
        db.session.rollback()  # Rollback transaction on error
        return jsonify({'error': str(e)}), 500

# 2) Allow initial_stock parameter when creating products
@app.route('/products', methods=['POST'])
def create_product():
    data = request.json
    product = Product(
        name=data['name'],
        price=data['price'],
        vat_rate=data['vat_rate'],
        low_stock_threshold=data['low_stock_threshold'],
        current_stock=data['current_stock'],
        initial_stock=data.get('initial_stock', 0)  # Allow initial_stock
    )
    db.session.add(product)
    db.session.commit()  # Commit transaction
    return jsonify({'message': 'Product created successfully'}), 201

# 3) PUT endpoint for customers to update their data
@app.route('/customers/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    data = request.json
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    try:
        customer.name = data.get('name', customer.name)
        customer.email = data.get('email', customer.email)
        # Add other fields as required
        db.session.commit()  # Commit transaction
        return jsonify({'message': 'Customer updated successfully'}), 200
    except Exception as e:
        db.session.rollback()  # Rollback transaction on error
        return jsonify({'error': str(e)}), 500

# 4) PUT endpoint for remissions to update payment status
@app.route('/remissions/<int:remission_id>', methods=['PUT'])
def update_remission(remission_id):
    data = request.json
    remission = Remission.query.get(remission_id)
    if not remission:
        return jsonify({'error': 'Remission not found'}), 404
    try:
        remission.payment_status = data.get('payment_status', remission.payment_status)
        remission.payment_notes = data.get('payment_notes', remission.payment_notes)
        remission.paid_amount = data.get('paid_amount', remission.paid_amount)
        db.session.commit()  # Commit transaction
        return jsonify({'message': 'Remission updated successfully'}), 200
    except Exception as e:
        db.session.rollback()  # Rollback transaction on error
        return jsonify({'error': str(e)}), 500

# 5) GET endpoint for sales reports in CSV format
@app.route('/sales/reports', methods=['GET'])
def get_sales_reports():
    try:
        # Logic to generate CSV report goes here
        # Example: sales_data = generate_sales_data()
        # return send_file(sales_data, mimetype='text/csv')
        return jsonify({'message': 'Sales report generated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)