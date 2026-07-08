# setup_db.py - Complete Fixed Version
import sys
try:
    import sqlite3
except ImportError:
    import pysqlite3 as sqlite3
    sys.modules['sqlite3'] = sqlite3

import os
import hashlib
import secrets
from datetime import datetime, timedelta

def hash_password(password):
    salt = secrets.token_hex(16)
    combined = password + salt
    hash_obj = hashlib.sha256(combined.encode())
    password_hash = hash_obj.hexdigest()
    return f"{salt}${password_hash}"

def create_database():
    if os.path.exists('shop_management.db'):
        print("⚠️ Database already exists!")
        response = input("Do you want to delete and recreate it? (y/n): ")
        if response.lower() != 'y':
            print("❌ Database creation cancelled.")
            return
        os.remove('shop_management.db')
        print("🗑️ Old database deleted.")
    
    conn = sqlite3.connect('shop_management.db')
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    
    print("📊 Creating database tables...")

    # ============================================
    # USERS TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'staff',
            avatar TEXT,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            is_verified BOOLEAN DEFAULT 0,
            reset_token TEXT,
            reset_token_expiry TIMESTAMP,
            theme_preference TEXT DEFAULT 'auto'
        )
    ''')
    print("✅ Users table created")

    # ============================================
    # SUPPLIERS TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            phone_secondary TEXT,
            email TEXT,
            address TEXT,
            shop_name TEXT,
            area TEXT,
            city TEXT,
            country TEXT DEFAULT 'Pakistan',
            total_due REAL DEFAULT 0,
            total_purchases REAL DEFAULT 0,
            credit_limit REAL,
            payment_terms TEXT,
            notes TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    print("✅ Suppliers table created")

    # ============================================
    # CUSTOMERS TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            phone_secondary TEXT,
            email TEXT,
            address TEXT,
            city TEXT,
            country TEXT DEFAULT 'Pakistan',
            total_due REAL DEFAULT 0,
            total_purchases REAL DEFAULT 0,
            total_visits INTEGER DEFAULT 0,
            discount_rate REAL DEFAULT 0,
            customer_type TEXT DEFAULT 'regular',
            credit_limit REAL,
            notes TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            last_purchase TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    print("✅ Customers table created")

    # ============================================
    # PRODUCTS TABLE - WITH ALL COLUMNS
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            sub_category TEXT,
            barcode TEXT UNIQUE,
            sku TEXT UNIQUE,
            purchase_price REAL NOT NULL DEFAULT 0,
            selling_price REAL NOT NULL DEFAULT 0,
            wholesale_price REAL,
            stock_quantity INTEGER DEFAULT 0,
            min_stock_level INTEGER DEFAULT 5,
            max_stock_level INTEGER DEFAULT 100,
            unit TEXT DEFAULT 'piece',
            weight REAL,
            color TEXT,
            brand TEXT,
            model TEXT,
            description TEXT,
            supplier_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            is_featured BOOLEAN DEFAULT 0,
            image_url TEXT,
            warehouse_location TEXT,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
    ''')
    print("✅ Products table created")

    # ============================================
    # SALES TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            sale_type TEXT NOT NULL,
            customer_id INTEGER,
            subtotal REAL NOT NULL DEFAULT 0,
            discount_type TEXT DEFAULT 'percentage',
            discount_value REAL DEFAULT 0,
            discount_amount REAL DEFAULT 0,
            tax_rate REAL DEFAULT 0,
            tax_amount REAL DEFAULT 0,
            shipping_charge REAL DEFAULT 0,
            total_amount REAL NOT NULL DEFAULT 0,
            payment_method TEXT,
            payment_status TEXT DEFAULT 'pending',
            amount_paid REAL DEFAULT 0,
            due_amount REAL DEFAULT 0,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            is_returned BOOLEAN DEFAULT 0,
            return_reason TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    print("✅ Sales table created")

    # ============================================
    # SALE ITEMS TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER,
            service_name TEXT,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL DEFAULT 0,
            cost_price REAL,
            discount REAL DEFAULT 0,
            total_price REAL NOT NULL DEFAULT 0,
            is_product BOOLEAN DEFAULT 1,
            is_returned BOOLEAN DEFAULT 0,
            returned_quantity INTEGER DEFAULT 0,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')
    print("✅ Sale Items table created")

    # ============================================
    # PURCHASES TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_number TEXT UNIQUE NOT NULL,
            supplier_id INTEGER,
            subtotal REAL NOT NULL DEFAULT 0,
            discount REAL DEFAULT 0,
            shipping_charge REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total_amount REAL NOT NULL DEFAULT 0,
            payment_status TEXT DEFAULT 'pending',
            amount_paid REAL DEFAULT 0,
            due_amount REAL DEFAULT 0,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            received_at TIMESTAMP,
            notes TEXT,
            is_returned BOOLEAN DEFAULT 0,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    print("✅ Purchases table created")
# setup_db.py mein yeh table add karein (products ke baad)

cursor.execute('''
    CREATE TABLE IF NOT EXISTS bill_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_type TEXT NOT NULL,
        customer_name TEXT,
        phone TEXT,
        bill_amount REAL NOT NULL,
        profit_amount REAL NOT NULL,
        reference_number TEXT,
        notes TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    )
''')
print("✅ Bill Payments table created")
    # ============================================
    # PURCHASE ITEMS TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL DEFAULT 0,
            total_price REAL NOT NULL DEFAULT 0,
            received_quantity INTEGER,
            is_returned BOOLEAN DEFAULT 0,
            FOREIGN KEY (purchase_id) REFERENCES purchases(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')
    print("✅ Purchase Items table created")

    # ============================================
    # PAYMENTS TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            purchase_id INTEGER,
            customer_id INTEGER,
            supplier_id INTEGER,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reference_number TEXT,
            notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (purchase_id) REFERENCES purchases(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    print("✅ Payments table created")

    # ============================================
    # CUSTOMER DUES TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_dues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            sale_id INTEGER,
            amount REAL NOT NULL,
            due_date TIMESTAMP,
            paid_amount REAL DEFAULT 0,
            remaining_amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (sale_id) REFERENCES sales(id)
        )
    ''')
    print("✅ Customer Dues table created")

    # ============================================
    # EXPENSES TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            sub_category TEXT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_method TEXT,
            receipt_number TEXT,
            vendor TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_recurring BOOLEAN DEFAULT 0,
            recurrence_interval TEXT,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    print("✅ Expenses table created")

    # ============================================
    # PHOTOCOPY JOBS TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photocopy_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_number TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            page_type TEXT NOT NULL,
            page_size TEXT DEFAULT 'A4',
            total_pages INTEGER NOT NULL,
            rate_per_page REAL NOT NULL DEFAULT 0,
            total_amount REAL NOT NULL DEFAULT 0,
            paper_used INTEGER NOT NULL DEFAULT 0,
            color_type TEXT,
            double_sided BOOLEAN DEFAULT 0,
            copies INTEGER DEFAULT 1,
            binding TEXT,
            status TEXT DEFAULT 'pending',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    print("✅ Photocopy Jobs table created")

    # ============================================
    # PAPER STOCK TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paper_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_type TEXT NOT NULL,
            paper_size TEXT NOT NULL,
            total_sheets INTEGER NOT NULL,
            used_sheets INTEGER DEFAULT 0,
            min_level INTEGER DEFAULT 100,
            max_level INTEGER DEFAULT 5000,
            brand TEXT,
            cost_per_sheet REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Paper Stock table created")

    # ============================================
    # STOCK MOVEMENTS TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            reference_id INTEGER,
            reference_type TEXT,
            previous_stock INTEGER,
            new_stock INTEGER,
            notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    print("✅ Stock Movements table created")

    # ============================================
    # AUDIT LOGS TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            table_name TEXT,
            record_id INTEGER,
            old_values TEXT,
            new_values TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    print("✅ Audit Logs table created")

    # ============================================
    # NOTIFICATIONS TABLE - WITH ALL COLUMNS
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            icon TEXT DEFAULT 'fa-info-circle',
            color TEXT DEFAULT '#2563EB',
            link TEXT,
            is_read BOOLEAN DEFAULT 0,
            read_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    print("✅ Notifications table created")

    # ============================================
    # BACKUPS TABLE
    # ============================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            backup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            size INTEGER,
            type TEXT,
            created_by INTEGER,
            notes TEXT,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    print("✅ Backups table created")

    # ============================================
    # SAMPLE DATA
    # ============================================
    print("\n📝 Inserting sample data...")
    
    admin_password = 'admin123'
    hashed = hash_password(admin_password)
    salt, hash_val = hashed.split('$')
    
    cursor.execute('''
        INSERT OR IGNORE INTO users 
        (username, email, password_hash, salt, full_name, role, is_verified, is_active, theme_preference)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('admin', 'admin@shop.com', hash_val, salt, 'System Administrator', 'admin', 1, 1, 'auto'))
    print("✅ Admin user added (password: admin123)")

    # Sample data continues...
    suppliers = [
        ('Shah Alami Traders', 'Ali Ahmed', '0300-1234567', 'shahalami@email.com', 
         'Shah Alami Market', 'Shah Alami Traders', 'Shah Alami', 'Karachi', 'Pakistan'),
        ('Hall Road Electronics', 'Usman Khan', '0301-7654321', 'hallroad@email.com',
         'Hall Road, Saddar', 'Hall Road Electronics', 'Saddar', 'Karachi', 'Pakistan'),
        ('Mobile Accessories Co', 'Sana Malik', '0302-9876543', 'mobileacc@email.com',
         'Tariq Road', 'Mobile Accessories Co', 'Tariq Road', 'Karachi', 'Pakistan'),
    ]
    for s in suppliers:
        cursor.execute('''INSERT OR IGNORE INTO suppliers (name, contact_person, phone, email, address, shop_name, area, city, country, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)''', s)
    print("✅ Sample suppliers added")

    customers = [
        ('Muhammad Bilal', '0311-2345678', 'bilal@gmail.com', 'House #12, Block 5', 'Karachi', 'regular'),
        ('Fatima Ali', '0312-8765432', 'fatima@gmail.com', 'Flat #3, Clifton', 'Karachi', 'vip'),
        ('Ahmed Hassan', '0313-4567890', 'ahmed@gmail.com', 'House #45, Gulshan', 'Karachi', 'wholesale'),
        ('Sara Khan', '0314-7890123', 'sara@gmail.com', 'Apartment #8, DHA', 'Karachi', 'regular'),
        ('Usman Siddiqui', '0315-3456789', 'usman@gmail.com', 'House #23, Nazimabad', 'Karachi', 'regular'),
    ]
    for c in customers:
        cursor.execute('''INSERT OR IGNORE INTO customers (name, phone, email, address, city, customer_type, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)''', c)
    print("✅ Sample customers added")

    products = [
        ('iPhone 13 Glass Protector', 'Screen Protectors', 'Tempered Glass', 'IPHONE13-GLASS', 150, 350, 280, 45, 10, 'piece', 'Apple', 'iPhone 13'),
        ('Samsung S22 Case', 'Phone Cases', 'Silicone', 'SAMSUNG-S22-CASE', 200, 500, 380, 30, 8, 'piece', 'Samsung', 'S22'),
        ('USB-C Cable 2m', 'Cables', 'Braided', 'USB-C-2M', 100, 250, 200, 80, 15, 'piece', 'Generic', 'USB-C'),
        ('Charger Adapter 20W', 'Chargers', 'Fast Charging', 'CHARGER-20W', 300, 800, 650, 40, 10, 'piece', 'Apple', '20W'),
        ('AirPods Case', 'Accessories', 'Silicone', 'AIRPODS-CASE', 250, 600, 450, 25, 5, 'piece', 'Generic', 'AirPods'),
        ('Phone Stand', 'Accessories', 'Desk', 'PHONE-STAND', 80, 200, 150, 55, 12, 'piece', 'Generic', 'Desk Stand'),
        ('Screen Cleaner Kit', 'Accessories', 'Cleaning', 'CLEANER-KIT', 120, 300, 250, 30, 10, 'piece', 'Generic', 'Cleaner'),
        ('Data Cable 1m', 'Cables', 'Nylon', 'DATA-CABLE-1M', 80, 180, 140, 70, 15, 'piece', 'Generic', '1M'),
        ('Samsung Note 20 Case', 'Phone Cases', 'Armor', 'SAMSUNG-NOTE20-CASE', 220, 450, 350, 20, 8, 'piece', 'Samsung', 'Note 20'),
        ('iPhone 12 Back Cover', 'Phone Cases', 'Clear', 'IPHONE12-COVER', 180, 400, 320, 35, 10, 'piece', 'Apple', 'iPhone 12'),
    ]
    for p in products:
        cursor.execute('''INSERT OR IGNORE INTO products (name, category, sub_category, barcode, purchase_price, selling_price, wholesale_price, stock_quantity, min_stock_level, unit, brand, model, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)''', p)
    print("✅ Sample products added")

    paper_stock = [
        ('b&w', 'A4', 5000, 0, 100, 5000),
        ('color', 'A4', 2000, 0, 100, 2000),
        ('b&w', 'A3', 1000, 0, 50, 1000),
        ('color', 'A3', 500, 0, 50, 500),
    ]
    for ps in paper_stock:
        cursor.execute('''INSERT OR IGNORE INTO paper_stock (paper_type, paper_size, total_sheets, used_sheets, min_level, max_level) VALUES (?, ?, ?, ?, ?, ?)''', ps)
    print("✅ Sample paper stock added")

    expenses = [
        ('Rent', 'Shop Rent', 'Monthly shop rent', 50000, 'cash'),
        ('Electricity', 'Utility', 'Electricity bill', 15000, 'bank'),
        ('Internet', 'Utility', 'Internet and phone bill', 5000, 'bank'),
        ('Salaries', 'Staff', 'Staff salaries', 30000, 'cash'),
        ('Stationery', 'Office', 'Office supplies', 3000, 'cash'),
    ]
    for e in expenses:
        cursor.execute('''INSERT OR IGNORE INTO expenses (category, sub_category, description, amount, payment_method, expense_date) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''', e)
    print("✅ Sample expenses added")

    conn.commit()
    
    print("\n✅ Database setup completed successfully!")
    conn.close()
    print("\n🎉 Database is ready! Run 'python app.py' to start the server.")
    print("🔑 Login: admin / admin123")

if __name__ == '__main__':
    create_database()
