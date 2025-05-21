from flask import Flask, request, jsonify
import sqlite3
import json
from datetime import datetime
import os

app = Flask(__name__)
DB_PATH = 'bookstore.db'

def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE books
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      title TEXT NOT NULL,
                      author TEXT NOT NULL,
                      price REAL NOT NULL,
                      stock INTEGER NOT NULL)''')
        c.execute('''CREATE TABLE orders
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER NOT NULL,
                      total REAL NOT NULL,
                      timestamp TEXT NOT NULL,
                      items TEXT NOT NULL)''')
        sample_books = [
            (1, '1984', 'George Orwell', 9.99, 50),
            (2, 'To Kill a Mockingbird', 'Harper Lee', 12.99, 30),
            (3, 'Pride and Prejudice', 'Jane Austen', 7.99, 40),
            (4, 'The Great Gatsby', 'F. Scott Fitzgerald', 10.99, 25),
            (5, 'Moby-Dick', 'Herman Melville', 11.99, 20)
        ]
        c.executemany('INSERT INTO books (id, title, author, price, stock) VALUES (?, ?, ?, ?, ?)', sample_books)
        conn.commit()
        conn.close()

@app.route('/api/books', methods=['GET'])
def get_books():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM books')
    books = [{'id': row[0], 'title': row[1], 'author': row[2], 'price': row[3], 'stock': row[4]} for row in c.fetchall()]
    conn.close()
    return jsonify(books), 200

@app.route('/api/books', methods=['POST'])
def add_book():
    data = request.get_json()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO books (title, author, price, stock) VALUES (?, ?, ?, ?)',
              (data['title'], data['author'], data['price'], data['stock']))
    conn.commit()
    book_id = c.lastrowid
    conn.close()
    return jsonify({'message': 'Book added', 'id': book_id}), 201

@app.route('/api/books/<int:id>', methods=['PUT'])
def update_book(id):
    data = request.get_json()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE books SET title = ?, author = ?, price = ?, stock = ? WHERE id = ?',
              (data['title'], data['author'], data['price'], data['stock'], id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Book updated'}), 200

@app.route('/api/books/<int:id>', methods=['DELETE'])
def delete_book(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM books WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Book deleted'}), 200

@app.route('/api/orders', methods=['GET'])
def get_orders():
    user_id = request.args.get('user_id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if user_id:
        c.execute('SELECT * FROM orders WHERE user_id = ?', (user_id,))
    else:
        c.execute('SELECT * FROM orders')
    orders = [{'id': row[0], 'user_id': row[1], 'total': row[2], 'timestamp': row[3], 'items': json.loads(row[4])} for row in c.fetchall()]
    conn.close()
    return jsonify(orders), 200

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    items = data['items']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Validate stock
    for item in items:
        c.execute('SELECT stock FROM books WHERE id = ?', (item['book_id'],))
        result = c.fetchone()
        if not result or result[0] < item['quantity']:
            conn.close()
            return jsonify({'error': f"Insufficient stock for book ID {item['book_id']}"}), 400
    # Calculate total and update stock
    total = sum(item['price'] * item['quantity'] for item in items)
    for item in items:
        c.execute('UPDATE books SET stock = stock - ? WHERE id = ?', (item['quantity'], item['book_id']))
    # Create order
    timestamp = datetime.utcnow().isoformat()
    c.execute('INSERT INTO orders (user_id, total, timestamp, items) VALUES (?, ?, ?, ?)',
              (data['user_id'], total, timestamp, json.dumps(items)))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Order created'}), 201

if __name__ == '__main__':
    init_db()
    app.run(debug=True)