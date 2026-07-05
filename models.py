# ============================================
# PRIMEACCESS - MODELS
# ============================================

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ============================================
# USER MODEL (Existing)
# ============================================
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='user')  # admin, manager, user
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    profile_image = db.Column(db.String(200), nullable=True)
    
    # Relationships
    sales = db.relationship('Sale', backref='user', lazy=True)
    purchases = db.relationship('Purchase', backref='user', lazy=True)
    expenses = db.relationship('Expense', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

# ============================================
# PRODUCT MODEL (Existing)
# ============================================
class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    barcode = db.Column(db.String(50), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    brand = db.Column(db.String(100), nullable=True)
    
    # Pricing
    purchase_price = db.Column(db.Float, default=0.0)
    selling_price = db.Column(db.Float, default=0.0)
    wholesale_price = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    
    # Stock
    quantity = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=5)
    max_stock_level = db.Column(db.Integer, default=100)
    reorder_point = db.Column(db.Integer, default=10)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sale_items = db.relationship('SaleItem', backref='product', lazy=True)
    purchase_items = db.relationship('PurchaseItem', backref='product', lazy=True)
    
    def __repr__(self):
        return f'<Product {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'sku': self.sku,
            'selling_price': self.selling_price,
            'quantity': self.quantity,
            'min_stock_level': self.min_stock_level
        }

# ============================================
# SALE MODEL (Existing)
# ============================================
class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Amounts
    subtotal = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    shipping = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    paid = db.Column(db.Float, default=0.0)
    due = db.Column(db.Float, default=0.0)
    
    # Status
    payment_status = db.Column(db.String(50), default='pending')  # paid, pending, partial, due
    order_status = db.Column(db.String(50), default='completed')  # pending, completed, cancelled, refunded
    
    # Payment
    payment_method = db.Column(db.String(50), nullable=True)  # cash, card, mobile_wallet, bank_transfer
    payment_date = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')
    customer = db.relationship('Customer', backref='sales', lazy=True)
    
    def __repr__(self):
        return f'<Sale {self.invoice_number}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'total': self.total,
            'payment_status': self.payment_status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

# ============================================
# SALE ITEM MODEL (Existing)
# ============================================
class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, default=0.0)  # Selling price at time of sale
    discount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f'<SaleItem {self.id}>'

# ============================================
# PURCHASE MODEL (Existing)
# ============================================
class Purchase(db.Model):
    __tablename__ = 'purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_order = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    subtotal = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    shipping = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    
    payment_status = db.Column(db.String(50), default='pending')  # paid, pending, partial
    payment_method = db.Column(db.String(50), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('PurchaseItem', backref='purchase', lazy=True, cascade='all, delete-orphan')
    supplier = db.relationship('Supplier', backref='purchases', lazy=True)
    
    def __repr__(self):
        return f'<Purchase {self.purchase_order}>'

# ============================================
# PURCHASE ITEM MODEL (Existing)
# ============================================
class PurchaseItem(db.Model):
    __tablename__ = 'purchase_items'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, default=0.0)  # Purchase price
    total = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f'<PurchaseItem {self.id}>'

# ============================================
# CUSTOMER MODEL (Existing)
# ============================================
class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(50), default='Pakistan')
    postal_code = db.Column(db.String(20), nullable=True)
    
    # Business
    company = db.Column(db.String(100), nullable=True)
    tax_id = db.Column(db.String(50), nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    total_purchases = db.Column(db.Float, default=0.0)
    total_orders = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Customer {self.name}>'

# ============================================
# SUPPLIER MODEL (Existing)
# ============================================
class Supplier(db.Model):
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(50), default='Pakistan')
    
    company = db.Column(db.String(100), nullable=True)
    tax_id = db.Column(db.String(50), nullable=True)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Supplier {self.name}>'

# ============================================
# EXPENSE MODEL (Existing)
# ============================================
class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # rent, utilities, salary, marketing, etc.
    description = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Float, default=0.0)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50), nullable=True)
    receipt = db.Column(db.String(200), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Expense {self.id}: {self.category}>'

# ============================================
# MOBILE WALLET MODEL (Existing)
# ============================================
class MobileWallet(db.Model):
    __tablename__ = 'mobile_wallets'
    
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)  # JazzCash, EasyPaisa, etc.
    account_number = db.Column(db.String(20), nullable=False)
    account_holder = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<MobileWallet {self.provider}>'

# ============================================
# PHOTOCOPY JOB MODEL (Existing)
# ============================================
class Photocopy(db.Model):
    __tablename__ = 'photocopies'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=True)
    
    # Job details
    job_type = db.Column(db.String(50), nullable=False)  # black_white, color, scanning, printing
    pages = db.Column(db.Integer, default=0)
    copies = db.Column(db.Integer, default=1)
    total_pages = db.Column(db.Integer, default=0)
    
    # Pricing
    price_per_page = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    
    # Status
    status = db.Column(db.String(50), default='pending')  # pending, completed, cancelled
    payment_status = db.Column(db.String(50), default='pending')  # paid, pending
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Photocopy {self.id}: {self.customer_name}>'

# ============================================
# ========== NEW: NOTIFICATION MODEL ==========
# ============================================
class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Null = all users
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')  # info, success, warning, danger, sale, stock, payment, user, system
    icon = db.Column(db.String(50), default='fa-info-circle')
    color = db.Column(db.String(20), default='#2563EB')
    link = db.Column(db.String(500), nullable=True)  # Clickable link
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)  # Auto-delete after expiry
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'
    
    def to_dict(self):
        """Convert notification to dictionary for API"""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'icon': self.icon,
            'color': self.color,
            'link': self.link,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'time_ago': self.get_time_ago()
        }
    
    def get_time_ago(self):
        """Calculate time ago in human readable format"""
        now = datetime.utcnow()
        diff = now - self.created_at
        
        if diff.days > 30:
            return f"{diff.days // 30} months ago"
        elif diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} minutes ago"
        else:
            return "Just now"