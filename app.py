# app.py - Complete Main Application with Bill Payment Feature
# ============ IMPORTS ============
from sqlalchemy import func, and_, or_, inspect, text
import io
import os
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
try:
    import sqlite3
except ImportError:
    import pysqlite3 as sqlite3
    sys.modules['sqlite3'] = sqlite3

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, make_response, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import shutil
from sqlalchemy import func, and_, or_
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from io import BytesIO
import qrcode
import secrets
import hashlib
from urllib.parse import quote

# ============ 🆕 NEW IMPORT - SUPABASE STORAGE ============
import requests

# Import language translations
from languages import t, TRANSLATIONS

app = Flask(__name__)
# Database configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Supabase PostgreSQL connection
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Fix for Supabase
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop_management.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ============ 🆕 SUPABASE STORAGE CONFIG ============
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://your-project.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', 'your-service-key')
USEFUL_TABLES = [
    'users',                    # Users
    'products',                 # Products
    'customers',                # Customers
    'suppliers',                # Suppliers
    'sales',                    # Sales
    'sale_items',               # Sale Items
    'purchases',                # Purchases
    'purchase_items',           # Purchase Items
    'expenses',                 # Expenses
    'photocopy_jobs',           # Photocopy Jobs
    'mobile_wallet_transactions', # Mobile Wallet
    'data_revenue',             # Data Revenue
    'notes',                    # Notes
    'paper_stock',              # Paper Stock
    'customer_dues',            # Customer Dues
    'payments',                 # Payments
    'bill_payments',            # 🆕 Bill Payments
]

# ==================== MODELS ====================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(200))
    role = db.Column(db.String(50), default='staff')
    avatar = db.Column(db.String(200))
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    reset_token = db.Column(db.String(100))
    reset_token_expiry = db.Column(db.DateTime)
    theme_preference = db.Column(db.String(20), default='auto')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self):
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.utcnow() + timedelta(hours=24)
        return self.reset_token

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    sub_category = db.Column(db.String(100))
    barcode = db.Column(db.String(50), unique=True)
    sku = db.Column(db.String(50), unique=True)
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    wholesale_price = db.Column(db.Float)
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=5)
    max_stock_level = db.Column(db.Integer, default=100)
    unit = db.Column(db.String(20), default='piece')
    weight = db.Column(db.Float)
    color = db.Column(db.String(50))
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    description = db.Column(db.Text)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    image_url = db.Column(db.String(500))
    warehouse_location = db.Column(db.String(50))
    
    supplier = db.relationship('Supplier', backref='products')
    sale_items = db.relationship('SaleItem', backref='product', lazy=True)
    purchase_items = db.relationship('PurchaseItem', backref='product', lazy=True)
    stock_movements = db.relationship('StockMovement', backref='product', lazy=True)

# ==================== DATA REVENUE MODEL ====================

class DataRevenue(db.Model):
    __tablename__ = 'data_revenue'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # movies, songs, cartoon, vlogs, other
    customer_name = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='data_revenues')

# ==================== 🆕 BILL PAYMENT MODEL ====================

class BillPayment(db.Model):
    __tablename__ = 'bill_payments'
    id = db.Column(db.Integer, primary_key=True)
    bill_type = db.Column(db.String(50), nullable=False)  # electricity, gas, water
    customer_name = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    bill_amount = db.Column(db.Float, nullable=False)
    profit_amount = db.Column(db.Float, nullable=False)  # 20 or 50 based on amount
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='bill_payments')

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    phone_secondary = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    shop_name = db.Column(db.String(200))
    area = db.Column(db.String(100))
    city = db.Column(db.String(100))
    country = db.Column(db.String(50), default='Pakistan')
    total_due = db.Column(db.Float, default=0)
    total_purchases = db.Column(db.Float, default=0)
    credit_limit = db.Column(db.Float)
    payment_terms = db.Column(db.String(100))
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    purchases = db.relationship('Purchase', backref='supplier', lazy=True)
    created_user = db.relationship('User', backref='created_suppliers')

# ==================== NOTES MODEL ====================

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False, default='')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='notes')

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    phone_secondary = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    country = db.Column(db.String(50), default='Pakistan')
    total_due = db.Column(db.Float, default=0)
    total_purchases = db.Column(db.Float, default=0)
    total_visits = db.Column(db.Integer, default=0)
    discount_rate = db.Column(db.Float, default=0)
    customer_type = db.Column(db.String(50), default='regular')
    credit_limit = db.Column(db.Float)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    last_purchase = db.Column(db.DateTime)
    
    sales = db.relationship('Sale', backref='customer', lazy=True)
    dues = db.relationship('CustomerDue', backref='customer', lazy=True)
    photocopy_jobs = db.relationship('PhotocopyJob', backref='customer_ref', lazy=True)
    created_user = db.relationship('User', backref='created_customers')

class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    sale_type = db.Column(db.String(50), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    subtotal = db.Column(db.Float, nullable=False)
    discount_type = db.Column(db.String(20), default='percentage')
    discount_value = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    tax_rate = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    shipping_charge = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(50), default='pending')
    amount_paid = db.Column(db.Float, default=0)
    due_amount = db.Column(db.Float, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    is_returned = db.Column(db.Boolean, default=False)
    return_reason = db.Column(db.Text)
    
    items = db.relationship('SaleItem', backref='sale', lazy=True)
    user = db.relationship('User', backref='sales')
    payments = db.relationship('Payment', backref='sale', lazy=True)

class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    service_name = db.Column(db.String(200))
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float)
    discount = db.Column(db.Float, default=0)
    total_price = db.Column(db.Float, nullable=False)
    is_product = db.Column(db.Boolean, default=True)
    is_returned = db.Column(db.Boolean, default=False)
    returned_quantity = db.Column(db.Integer, default=0)

class Purchase(db.Model):
    __tablename__ = 'purchases'
    id = db.Column(db.Integer, primary_key=True)
    purchase_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    subtotal = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0)
    shipping_charge = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(50), default='pending')
    amount_paid = db.Column(db.Float, default=0)
    due_amount = db.Column(db.Float, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    received_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    is_returned = db.Column(db.Boolean, default=False)
    
    items = db.relationship('PurchaseItem', backref='purchase', lazy=True)
    user = db.relationship('User', backref='purchases')

class PurchaseItem(db.Model):
    __tablename__ = 'purchase_items'
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    received_quantity = db.Column(db.Integer)
    is_returned = db.Column(db.Boolean, default=False)
# ============ REPAIR REVENUE MODEL ============
class RepairRevenue(db.Model):
    __tablename__ = 'repair_revenue'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    device = db.Column(db.String(200), nullable=False)
    issue = db.Column(db.Text, nullable=False)
    customer_amount = db.Column(db.Float, nullable=False)
    parts_cost = db.Column(db.Float, nullable=False)
    profit = db.Column(db.Float, nullable=False)  # customer_amount - parts_cost
    status = db.Column(db.String(50), default='pending')
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='repairs')


# ============ OTHER REVENUE MODEL ============
class OtherRevenue(db.Model):
    __tablename__ = 'other_revenue'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), default='other')
    customer_name = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='other_revenues')
class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'))
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    customer = db.relationship('Customer', backref='payments')
    supplier = db.relationship('Supplier', backref='payments')
    user = db.relationship('User', backref='payments')

class CustomerDue(db.Model):
    __tablename__ = 'customer_dues'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'))
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.DateTime)
    paid_amount = db.Column(db.Float, default=0)
    remaining_amount = db.Column(db.Float)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    
    sale = db.relationship('Sale', backref='dues')

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    sub_category = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    expense_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50))
    receipt_number = db.Column(db.String(50))
    vendor = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_interval = db.Column(db.String(50))
    
    user = db.relationship('User', backref='expenses')

class PhotocopyJob(db.Model):
    __tablename__ = 'photocopy_jobs'
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    page_type = db.Column(db.String(50), nullable=False)
    page_size = db.Column(db.String(20), default='A4')
    total_pages = db.Column(db.Integer, nullable=False)
    rate_per_page = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    paper_used = db.Column(db.Integer, nullable=False)
    color_type = db.Column(db.String(20))
    double_sided = db.Column(db.Boolean, default=False)
    copies = db.Column(db.Integer, default=1)
    binding = db.Column(db.String(50))
    status = db.Column(db.String(50), default='pending')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    customer = db.relationship('Customer', backref='photocopy_jobs_ref')
    user = db.relationship('User', backref='photocopy_jobs_created')

class PaperStock(db.Model):
    __tablename__ = 'paper_stock'
    id = db.Column(db.Integer, primary_key=True)
    paper_type = db.Column(db.String(50), nullable=False)
    paper_size = db.Column(db.String(20), nullable=False)
    total_sheets = db.Column(db.Integer, nullable=False)
    used_sheets = db.Column(db.Integer, default=0)
    min_level = db.Column(db.Integer, default=100)
    max_level = db.Column(db.Integer, default=5000)
    brand = db.Column(db.String(100))
    cost_per_sheet = db.Column(db.Float)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StockMovement(db.Model):
    __tablename__ = 'stock_movements'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    movement_type = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    reference_id = db.Column(db.Integer)
    reference_type = db.Column(db.String(50))
    previous_stock = db.Column(db.Integer)
    new_stock = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='stock_movements')

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    old_values = db.Column(db.Text)
    new_values = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='audit_logs')

class Backup(db.Model):
    __tablename__ = 'backups'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    backup_date = db.Column(db.DateTime, default=datetime.utcnow)
    size = db.Column(db.Integer)
    type = db.Column(db.String(50))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')
    icon = db.Column(db.String(50), default='fa-info-circle')
    color = db.Column(db.String(20), default='#2563EB')
    link = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))
    
    def to_dict(self):
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

class MobileWalletTransaction(db.Model):
    __tablename__ = 'mobile_wallet_transactions'
    id = db.Column(db.Integer, primary_key=True)
    wallet_type = db.Column(db.String(50), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    amount = db.Column(db.Float, nullable=False)
    transaction_id = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    customer_name = db.Column(db.String(200))
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='completed')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    customer = db.relationship('Customer', backref='wallet_transactions')
    user = db.relationship('User', backref='wallet_transactions')

# ==================== LOGIN MANAGER ====================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============ 🆕 SUPABASE STORAGE HELPERS ============

def upload_to_supabase_storage(file_data, filename, bucket='backups'):
    """Upload file to Supabase Storage"""
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{filename}"
        headers = {
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, data=file_data)
        if response.status_code in [200, 201]:
            print(f"✅ File uploaded: {filename}")
            return True
        else:
            print(f"❌ Upload failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return False

def download_from_supabase_storage(filename, bucket='backups'):
    """Download file from Supabase Storage"""
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{filename}"
        headers = {
            'Authorization': f'Bearer {SUPABASE_KEY}'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return BytesIO(response.content)
        return None
    except Exception as e:
        print(f"❌ Download error: {str(e)}")
        return None

def delete_from_supabase_storage(filename, bucket='backups'):
    """Delete file from Supabase Storage"""
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{filename}"
        headers = {
            'Authorization': f'Bearer {SUPABASE_KEY}'
        }
        response = requests.delete(url, headers=headers)
        if response.status_code in [200, 204]:
            print(f"✅ File deleted: {filename}")
            return True
        return False
    except Exception as e:
        print(f"❌ Delete error: {str(e)}")
        return False

# ==================== CONTEXT PROCESSORS ====================

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.context_processor
def inject_theme():
    """Inject theme variables in all templates"""
    theme = session.get('theme', 'light')
    theme_mode = session.get('theme_mode', 'auto')
    color_theme = session.get('color_theme', 'default')
    
    return {
        'current_theme': theme,
        'theme_mode': theme_mode,
        'color_theme': color_theme,
        'is_light': theme == 'light',
        'is_dark': theme == 'dark',
        'is_auto': theme_mode == 'auto',
        'is_light_sensor': theme_mode == 'light-sensor'
    }

@app.context_processor
def inject_language():
    """Inject language functions in all templates"""
    lang = session.get('language', 'en')
    return {
        'current_lang': lang,
        'is_urdu': lang == 'ur',
        't': t
    }

# ==================== ROUTES ====================

# ---------- Authentication Routes ----------

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            log = AuditLog(user_id=user.id, action='login', table_name='users', 
                          record_id=user.id, ip_address=request.remote_addr,
                          user_agent=request.headers.get('User-Agent'))
            db.session.add(log)
            db.session.commit()
            
            next_page = request.args.get('next')
            flash('Welcome back, {}!'.format(user.full_name or user.username), 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log = AuditLog(user_id=current_user.id, action='logout', table_name='users',
                   record_id=current_user.id, ip_address=request.remote_addr,
                   user_agent=request.headers.get('User-Agent'))
    db.session.add(log)
    db.session.commit()
    
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')
        
        user = User(username=username, email=email, full_name=full_name, role='staff')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            flash('Password reset link has been sent to your email.', 'info')
            return redirect(url_for('login'))
        else:
            flash('Email not found.', 'danger')
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or user.reset_token_expiry < datetime.utcnow():
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html')
        
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        flash('Password reset successfully! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

# ============ DATA REVENUE ROUTES ============

@app.route('/data_revenue')
@login_required
def data_revenue():
    """Data/Content Revenue Management"""
    revenues = DataRevenue.query.order_by(DataRevenue.created_at.desc()).all()
    
    # Category totals
    category_totals = {}
    categories = ['movies', 'songs', 'cartoon', 'vlogs', 'other']
    for cat in categories:
        total = db.session.query(func.sum(DataRevenue.amount)).filter(
            DataRevenue.category == cat
        ).scalar() or 0
        category_totals[cat] = total
    
    total_data_revenue = sum(category_totals.values())
    
    return render_template('data_revenue.html', 
                         revenues=revenues,
                         category_totals=category_totals,
                         total_data_revenue=total_data_revenue)

@app.route('/data_revenue/add', methods=['POST'])
@login_required
def add_data_revenue():
    """Add data revenue"""
    category = request.form.get('category')
    customer_name = request.form.get('customer_name')
    phone = request.form.get('phone')
    amount = float(request.form.get('amount'))
    description = request.form.get('description')
    
    revenue = DataRevenue(
        category=category,
        customer_name=customer_name,
        phone=phone,
        amount=amount,
        description=description,
        created_by=current_user.id
    )
    db.session.add(revenue)
    db.session.commit()
    
    flash(f'✅ Data revenue added: {category} - PKR {amount:,.0f}', 'success')
    return redirect(url_for('data_revenue'))

@app.route('/data_revenue/delete/<int:revenue_id>', methods=['POST'])
@login_required
def delete_data_revenue(revenue_id):
    """Delete data revenue"""
    revenue = DataRevenue.query.get_or_404(revenue_id)
    db.session.delete(revenue)
    db.session.commit()
    flash('✅ Data revenue deleted!', 'success')
    return jsonify({'status': 'success'})

# ============ 🆕 BILL PAYMENT ROUTES ============

@app.route('/bill_payment')
@login_required
def bill_payment():
    """Bill Payment page"""
    bills = BillPayment.query.order_by(BillPayment.created_at.desc()).all()
    total_bills = len(bills)
    total_profit = db.session.query(func.sum(BillPayment.profit_amount)).scalar() or 0
    
    # Count by type
    bill_counts = {}
    for bill_type in ['electricity', 'gas', 'water']:
        count = BillPayment.query.filter_by(bill_type=bill_type).count()
        bill_counts[bill_type] = count
    
    return render_template('bill_payment.html', 
                         bills=bills, 
                         total_bills=total_bills,
                         total_profit=total_profit,
                         bill_counts=bill_counts)

@app.route('/bill_payment/add', methods=['POST'])
@login_required
def add_bill_payment():
    """Add new bill payment"""
    bill_type = request.form.get('bill_type')
    bill_amount = float(request.form.get('bill_amount'))
    customer_name = request.form.get('customer_name')
    phone = request.form.get('phone')
    reference_number = request.form.get('reference_number')
    notes = request.form.get('notes')
    
    # Calculate profit: < 5000 = 20, >= 5000 = 50
    profit_amount = 20 if bill_amount < 5000 else 50
    
    bill = BillPayment(
        bill_type=bill_type,
        customer_name=customer_name,
        phone=phone,
        bill_amount=bill_amount,
        profit_amount=profit_amount,
        reference_number=reference_number,
        notes=notes,
        created_by=current_user.id
    )
    
    db.session.add(bill)
    db.session.commit()
    
    create_notification(
        user_id=None,
        title="📄 New Bill Payment!",
        message=f"{bill_type.title()} bill - Profit: PKR {profit_amount:,.0f}",
        type='payment',
        link='/bill_payment'
    )
    db.session.commit()
    
    flash(f'✅ Bill payment added! Profit: PKR {profit_amount:,.0f}', 'success')
    return redirect(url_for('bill_payment'))

@app.route('/bill_payment/delete/<int:bill_id>', methods=['POST'])
@login_required
def delete_bill_payment(bill_id):
    """Delete bill payment"""
    bill = BillPayment.query.get_or_404(bill_id)
    db.session.delete(bill)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # ============ 1. PRODUCT SALES (Today) ============
    today_sales = Sale.query.filter(Sale.created_at.between(today_start, today_end)).all()
    total_sales_today = sum(sale.total_amount for sale in today_sales)
    total_sales_count = len(today_sales)
    
    # ============ 2. PHOTOCOPY REVENUE (Today) ============
    today_photocopy = PhotocopyJob.query.filter(PhotocopyJob.created_at.between(today_start, today_end)).all()
    total_prints_today = sum(job.total_pages for job in today_photocopy)
    total_photocopy_revenue = sum(job.total_amount for job in today_photocopy)
    
    # ============ 3. MOBILE WALLET - TODAY'S RECEIVE ============
    today_wallet_receive = MobileWalletTransaction.query.filter(
        MobileWalletTransaction.created_at.between(today_start, today_end),
        MobileWalletTransaction.transaction_type == 'receive'
    ).all()
    total_wallet_receive_today = sum(t.amount for t in today_wallet_receive)
    
    # ============ 4. MOBILE WALLET - TODAY'S SEND ============
    today_wallet_send = MobileWalletTransaction.query.filter(
        MobileWalletTransaction.created_at.between(today_start, today_end),
        MobileWalletTransaction.transaction_type == 'send'
    ).all()
    total_wallet_send_today = sum(t.amount for t in today_wallet_send)
    
    # ============ 5. WALLET PROFIT (Today) ============
    # Rule: Send = 1% profit, Receive = 2% profit
    today_wallet_profit = (total_wallet_send_today * 0.01) + (total_wallet_receive_today * 0.02)
    
    # ============ 6. DATA REVENUE (Today) ============
    today_data_revenue = DataRevenue.query.filter(
        DataRevenue.created_at.between(today_start, today_end)
    ).all()
    total_data_revenue_today = sum(r.amount for r in today_data_revenue)
    
    # ============ 🆕 7. BILL PAYMENT PROFIT (Today) ============
    today_bills = BillPayment.query.filter(
        BillPayment.created_at.between(today_start, today_end)
    ).all()
    today_bill_profit = sum(b.profit_amount for b in today_bills)
    
    # ============ 8. TOTAL REVENUE (Today) - UPDATED ============
    # Product Sales + Photocopy Revenue + Wallet Profit + Data Revenue + Bill Profit
    total_revenue_today = total_sales_today + total_photocopy_revenue + today_wallet_profit + total_data_revenue_today + today_bill_profit
    
    # ============ 9. EXPENSES (Today) ============
    today_expenses = Expense.query.filter(Expense.expense_date.between(today_start, today_end)).all()
    total_expenses_today = sum(expense.amount for expense in today_expenses)
    
    # ============ 10. NET PROFIT (Today) ============
    net_profit_today = total_revenue_today - total_expenses_today
    
    # ============ 11. DUES (Today) ============
    today_dues = CustomerDue.query.filter(CustomerDue.due_date.between(today_start, today_end), 
                                         CustomerDue.status == 'pending').all()
    due_amount_today = sum(due.remaining_amount or due.amount for due in today_dues)
    
    # ============ 12. STOCK ALERTS ============
    low_stock = Product.query.filter(Product.stock_quantity <= Product.min_stock_level).all()
    out_of_stock = Product.query.filter(Product.stock_quantity == 0).all()
    
    # ============ 13. MONTHLY SALES ============
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_sales = Sale.query.filter(Sale.created_at >= month_start).all()
    total_monthly_sales = sum(sale.total_amount for sale in monthly_sales)
    
    # ============ 14. WEEKLY SALES ============
    week_start = datetime.now() - timedelta(days=7)
    weekly_sales = Sale.query.filter(Sale.created_at >= week_start).all()
    total_weekly_sales = sum(sale.total_amount for sale in weekly_sales)
    
    # ============ 15. RECENT ACTIVITY ============
    recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(10).all()
    recent_photocopy = PhotocopyJob.query.order_by(PhotocopyJob.created_at.desc()).limit(5).all()
    recent_expenses = Expense.query.order_by(Expense.expense_date.desc()).limit(5).all()
    
    # ============ 16. CUSTOMERS ============
    total_customers = Customer.query.count()
    new_customers_today = Customer.query.filter(Customer.created_at.between(today_start, today_end)).count()
    
    # ============ 17. PRODUCTS ============
    total_products = Product.query.filter_by(is_active=True).count()
    total_products_value = db.session.query(func.sum(Product.purchase_price * Product.stock_quantity)).scalar() or 0
    
    # ============ 18. DAILY SALES DATA (for chart) ============
    days = [(datetime.now() - timedelta(days=i)).date() for i in range(7, -1, -1)]
    daily_sales_data = []
    for day in days:
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        day_sales = Sale.query.filter(Sale.created_at.between(day_start, day_end)).all()
        daily_sales_data.append(sum(sale.total_amount for sale in day_sales))
    
    # ============ 19. TOP PRODUCTS ============
    top_products = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_sold')
    ).join(SaleItem).group_by(Product.id).order_by(func.sum(SaleItem.quantity).desc()).limit(10).all()
    
    # ============ 20. PAYMENT METHODS ============
    payment_methods = db.session.query(
        Sale.payment_method,
        func.count(Sale.id).label('count'),
        func.sum(Sale.total_amount).label('total')
    ).group_by(Sale.payment_method).all()
    
    # ============ 21. WALLET BALANCE (Overall) ============
    total_received_jazz = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.wallet_type == 'jazzcash',
        MobileWalletTransaction.transaction_type == 'receive'
    ).scalar() or 0
    
    total_sent_jazz = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.wallet_type == 'jazzcash',
        MobileWalletTransaction.transaction_type == 'send'
    ).scalar() or 0
    
    total_received_easy = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.wallet_type == 'easypaisa',
        MobileWalletTransaction.transaction_type == 'receive'
    ).scalar() or 0
    
    total_sent_easy = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.wallet_type == 'easypaisa',
        MobileWalletTransaction.transaction_type == 'send'
    ).scalar() or 0
    
    balance_jazz = total_received_jazz - total_sent_jazz
    balance_easy = total_received_easy - total_sent_easy
    total_wallet_balance = balance_jazz + balance_easy
    
    # ============ 22. OVERALL WALLET PROFIT (All time) ============
    total_wallet_send_all = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.transaction_type == 'send'
    ).scalar() or 0
    
    total_wallet_receive_all = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.transaction_type == 'receive'
    ).scalar() or 0
    
    wallet_profit_all = (total_wallet_send_all * 0.01) + (total_wallet_receive_all * 0.02)
    
    # ============ 23. OVERALL DATA REVENUE (All time) ============
    total_data_revenue_all = db.session.query(func.sum(DataRevenue.amount)).scalar() or 0
    
    # ============ 🆕 24. OVERALL BILL PROFIT (All time) ============
    total_bill_profit_all = db.session.query(func.sum(BillPayment.profit_amount)).scalar() or 0
    
    # ============ CONTEXT ============
    context = {
        # ===== REVENUE (Today) =====
        'total_sales_today': total_sales_today,
        'total_sales_count': total_sales_count,
        'total_photocopy_revenue': total_photocopy_revenue,
        'total_wallet_receive_today': total_wallet_receive_today,
        'total_wallet_send_today': total_wallet_send_today,
        'today_wallet_profit': today_wallet_profit,
        'total_data_revenue_today': total_data_revenue_today,
        'today_bill_profit': today_bill_profit,  # 🆕
        'total_revenue_today': total_revenue_today,
        'total_prints_today': total_prints_today,
        
        # ===== WALLET PROFIT (Overall) =====
        'wallet_profit': wallet_profit_all,
        
        # ===== DATA REVENUE (Overall) =====
        'total_data_revenue_all': total_data_revenue_all,
        
        # ===== BILL PROFIT (Overall) =====
        'total_bill_profit_all': total_bill_profit_all,  # 🆕
        
        # ===== EXPENSES & PROFIT =====
        'total_expenses_today': total_expenses_today,
        'net_profit_today': net_profit_today,
        'due_amount_today': due_amount_today,
        
        # ===== STOCK =====
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'low_stock_count': len(low_stock),
        'out_of_stock_count': len(out_of_stock),
        
        # ===== MONTHLY/WEEKLY =====
        'total_monthly_sales': total_monthly_sales,
        'total_weekly_sales': total_weekly_sales,
        
        # ===== RECENT =====
        'recent_sales': recent_sales,
        'recent_photocopy': recent_photocopy,
        'recent_expenses': recent_expenses,
        
        # ===== CUSTOMERS =====
        'total_customers': total_customers,
        'new_customers_today': new_customers_today,
        
        # ===== PRODUCTS =====
        'total_products': total_products,
        'total_products_value': total_products_value,
        
        # ===== CHARTS =====
        'daily_sales_data': daily_sales_data,
        'days': days,
        'top_products': top_products,
        'payment_methods': payment_methods,
        
        # ===== WALLET BALANCE =====
        'balance_jazz': balance_jazz,
        'balance_easy': balance_easy,
        'total_wallet_balance': total_wallet_balance,
    }
    
    return render_template('dashboard.html', **context)

# ============================================
# ALL OTHER ROUTES (Products, Sales, Purchases, Customers, Suppliers, Photocopy, Expenses, Reports, Backup, Settings, etc.)
# ============================================

# ---------- Product Management Routes ----------

@app.route('/products')
@login_required
def products():
    products = Product.query.filter_by(is_active=True).all()
    categories = db.session.query(Product.category).distinct().all()
    sub_categories = db.session.query(Product.sub_category).distinct().all()
    brands = db.session.query(Product.brand).distinct().all()
    suppliers = Supplier.query.filter_by(is_active=True).all()
    
    return render_template('products.html', 
                         products=products, 
                         categories=categories, 
                         sub_categories=sub_categories,
                         brands=brands,
                         suppliers=suppliers)

@app.route('/products/trash')
@login_required
def products_trash():
    products = Product.query.filter_by(is_active=False).all()
    return render_template('products_trash.html', products=products)

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        category_code = request.form.get('category', 'GEN')[:3].upper()
        product_count = Product.query.count() + 1
        sku = f"{category_code}-{product_count:05d}"
        
        product = Product(
            name=request.form.get('name'),
            category=request.form.get('category'),
            sub_category=request.form.get('sub_category'),
            barcode=request.form.get('barcode') or sku,
            sku=sku,
            purchase_price=float(request.form.get('purchase_price')),
            selling_price=float(request.form.get('selling_price')),
            wholesale_price=float(request.form.get('wholesale_price')) if request.form.get('wholesale_price') else None,
            stock_quantity=int(request.form.get('stock_quantity', 0)),
            min_stock_level=int(request.form.get('min_stock_level', 5)),
            max_stock_level=int(request.form.get('max_stock_level', 100)),
            unit=request.form.get('unit', 'piece'),
            weight=float(request.form.get('weight')) if request.form.get('weight') else None,
            color=request.form.get('color'),
            brand=request.form.get('brand'),
            model=request.form.get('model'),
            description=request.form.get('description'),
            supplier_id=int(request.form.get('supplier_id')) if request.form.get('supplier_id') else None,
            warehouse_location=request.form.get('warehouse_location'),
            is_featured=True if request.form.get('is_featured') else False
        )
        
        db.session.add(product)
        db.session.flush()
        
        if product.stock_quantity > 0:
            movement = StockMovement(
                product_id=product.id,
                movement_type='initial_stock',
                quantity=product.stock_quantity,
                previous_stock=0,
                new_stock=product.stock_quantity,
                notes='Initial stock entry',
                created_by=current_user.id
            )
            db.session.add(movement)
        
        log = AuditLog(
            user_id=current_user.id,
            action='create',
            table_name='products',
            record_id=product.id,
            new_values=json.dumps({'name': product.name, 'sku': product.sku}),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        
        db.session.commit()

        create_notification(
            user_id=None,
            title="📦 New Product Added!",
            message=f"{product.name} has been added to inventory (SKU: {product.sku})",
            type='success',
            link='/products'
        )
        db.session.commit()
        flash('Product added successfully! SKU: {}'.format(sku), 'success')
        return redirect(url_for('products'))
    
    suppliers = Supplier.query.filter_by(is_active=True).all()
    return render_template('add_product.html', suppliers=suppliers)

@app.route('/update_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        old_stock = product.stock_quantity
        old_name = product.name
        
        product.name = request.form.get('name')
        product.category = request.form.get('category')
        product.sub_category = request.form.get('sub_category')
        product.barcode = request.form.get('barcode')
        product.purchase_price = float(request.form.get('purchase_price'))
        product.selling_price = float(request.form.get('selling_price'))
        product.wholesale_price = float(request.form.get('wholesale_price')) if request.form.get('wholesale_price') else None
        product.min_stock_level = int(request.form.get('min_stock_level', 5))
        product.max_stock_level = int(request.form.get('max_stock_level', 100))
        product.unit = request.form.get('unit', 'piece')
        product.weight = float(request.form.get('weight')) if request.form.get('weight') else None
        product.color = request.form.get('color')
        product.brand = request.form.get('brand')
        product.model = request.form.get('model')
        product.description = request.form.get('description')
        product.supplier_id = int(request.form.get('supplier_id')) if request.form.get('supplier_id') else None
        product.warehouse_location = request.form.get('warehouse_location')
        product.is_featured = True if request.form.get('is_featured') else False
        product.last_updated = datetime.utcnow()
        
        new_stock = int(request.form.get('stock_quantity', 0))
        if new_stock != old_stock:
            movement = StockMovement(
                product_id=product.id,
                movement_type='stock_adjustment',
                quantity=new_stock - old_stock,
                previous_stock=old_stock,
                new_stock=new_stock,
                notes='Manual stock adjustment',
                created_by=current_user.id
            )
            db.session.add(movement)
            product.stock_quantity = new_stock
        
        log = AuditLog(
            user_id=current_user.id,
            action='update',
            table_name='products',
            record_id=product.id,
            old_values=json.dumps({'name': old_name}),
            new_values=json.dumps({'name': product.name}),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('products'))
    
    suppliers = Supplier.query.filter_by(is_active=True).all()
    return render_template('update_product.html', product=product, suppliers=suppliers)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = False
    
    log = AuditLog(
        user_id=current_user.id,
        action='delete',
        table_name='products',
        record_id=product.id,
        new_values=json.dumps({'deleted': True}),
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(log)
    db.session.commit()
    
    flash('Product moved to trash.', 'warning')
    return jsonify({'status': 'success'})

@app.route('/restore_product/<int:product_id>', methods=['POST'])
@login_required
def restore_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = True
    db.session.commit()
    flash('Product restored successfully!', 'success')
    return jsonify({'status': 'success'})

@app.route('/products/bulk_delete', methods=['POST'])
@login_required
def bulk_delete_products():
    product_ids = request.json.get('product_ids', [])
    products = Product.query.filter(Product.id.in_(product_ids)).all()
    for product in products:
        product.is_active = False
    db.session.commit()
    flash('Products deleted successfully!', 'success')
    return jsonify({'status': 'success'})

# ============ NOTES ROUTES - DATABASE VERSION ============

@app.route('/notes')
@login_required
def notes():
    """Simple notepad for shopkeeper - Database version"""
    # Get or create note for current user
    note = Note.query.filter_by(created_by=current_user.id).first()
    if not note:
        note = Note(content='', created_by=current_user.id)
        db.session.add(note)
        db.session.commit()
    
    return render_template('notes.html', note=note)

@app.route('/api/notes/save', methods=['POST'])
@login_required
def save_note():
    """Save note to database"""
    data = request.json
    content = data.get('content', '')
    
    note = Note.query.filter_by(created_by=current_user.id).first()
    if not note:
        note = Note(content=content, created_by=current_user.id)
        db.session.add(note)
    else:
        note.content = content
        note.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Note saved successfully',
        'updated_at': note.updated_at.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/notes/get', methods=['GET'])
@login_required
def get_note():
    """Get note from database"""
    note = Note.query.filter_by(created_by=current_user.id).first()
    if note:
        return jsonify({
            'status': 'success',
            'content': note.content,
            'updated_at': note.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        return jsonify({
            'status': 'success',
            'content': '',
            'updated_at': None
        })

@app.route('/api/notes/clear', methods=['POST'])
@login_required
def clear_note():
    """Clear note from database"""
    note = Note.query.filter_by(created_by=current_user.id).first()
    if note:
        note.content = ''
        note.updated_at = datetime.utcnow()
        db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Note cleared successfully'
    })

# ============ PAPER STOCK ROUTES ============

@app.route('/paper_stock')
@login_required
def paper_stock():
    """Paper stock management"""
    papers = PaperStock.query.all()
    return render_template('paper_stock.html', papers=papers)

@app.route('/paper_stock/add')
@login_required
def add_paper_stock_page():
    """Add paper stock page"""
    return render_template('add_paper_stock.html')

@app.route('/paper_stock/add', methods=['POST'])
@login_required
def add_paper_stock():
    """Add paper stock - POST"""
    paper_type = request.form.get('paper_type')
    paper_size = request.form.get('paper_size')
    total_sheets = int(request.form.get('total_sheets'))
    min_level = int(request.form.get('min_level', 100))
    max_level = int(request.form.get('max_level', 5000))
    
    paper = PaperStock(
        paper_type=paper_type,
        paper_size=paper_size,
        total_sheets=total_sheets,
        used_sheets=0,
        min_level=min_level,
        max_level=max_level
    )
    db.session.add(paper)
    db.session.commit()
    
    flash('✅ Paper stock added successfully!', 'success')
    return redirect(url_for('paper_stock'))

@app.route('/paper_stock/edit/<int:paper_id>')
@login_required
def edit_paper_stock_page(paper_id):
    """Edit paper stock page"""
    paper = PaperStock.query.get_or_404(paper_id)
    return render_template('edit_paper_stock.html', paper=paper)

@app.route('/paper_stock/update/<int:paper_id>', methods=['POST'])
@login_required
def update_paper_stock(paper_id):
    """Update paper stock - POST"""
    paper = PaperStock.query.get_or_404(paper_id)
    paper.total_sheets = int(request.form.get('total_sheets'))
    paper.min_level = int(request.form.get('min_level'))
    paper.max_level = int(request.form.get('max_level'))
    db.session.commit()
    
    flash('✅ Paper stock updated successfully!', 'success')
    return redirect(url_for('paper_stock'))

@app.route('/api/paper_stock/<int:paper_id>')
@login_required
def api_paper_stock(paper_id):
    """Get paper stock data for editing"""
    paper = PaperStock.query.get_or_404(paper_id)
    return jsonify({
        'status': 'success',
        'id': paper.id,
        'paper_type': paper.paper_type,
        'paper_size': paper.paper_size,
        'total_sheets': paper.total_sheets,
        'used_sheets': paper.used_sheets,
        'min_level': paper.min_level,
        'max_level': paper.max_level
    })

# ---------- Sale Routes ----------

@app.route('/sales')
@login_required
def sales():
    sales = Sale.query.order_by(Sale.created_at.desc()).all()
    return render_template('sales.html', sales=sales)

@app.route('/new_sale', methods=['GET', 'POST'])
@login_required
def new_sale():
    if request.method == 'POST':
        sale_type = request.form.get('sale_type')
        customer_id = request.form.get('customer_id')
        payment_method = request.form.get('payment_method')
        
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        prices = request.form.getlist('price[]')
        
        subtotal = 0
        sale_items = []
        
        for i in range(len(product_ids)):
            if product_ids[i] and quantities[i]:
                product = Product.query.get(int(product_ids[i]))
                if product:
                    quantity = int(quantities[i])
                    price = float(prices[i]) if prices[i] else product.selling_price
                    total = quantity * price
                    subtotal += total
                    
                    if product.stock_quantity >= quantity:
                        product.stock_quantity -= quantity
                        
                        movement = StockMovement(
                            product_id=product.id,
                            movement_type='sale',
                            quantity=-quantity,
                            previous_stock=product.stock_quantity + quantity,
                            new_stock=product.stock_quantity,
                            notes=f'Sale invoice #{request.form.get("invoice_number", "")}',
                            created_by=current_user.id
                        )
                        db.session.add(movement)
                    else:
                        flash(f'Insufficient stock for {product.name}. Available: {product.stock_quantity}', 'danger')
                        return redirect(url_for('new_sale'))
                    
                    sale_items.append({
                        'product_id': product.id,
                        'quantity': quantity,
                        'unit_price': price,
                        'total_price': total,
                        'is_product': True
                    })
        
        discount_type = request.form.get('discount_type', 'percentage')
        discount_value = float(request.form.get('discount_value', 0))
        
        if discount_type == 'percentage':
            discount_amount = subtotal * (discount_value / 100)
        else:
            discount_amount = discount_value
        
        tax_rate = float(request.form.get('tax_rate', 0))
        tax_amount = (subtotal - discount_amount) * (tax_rate / 100)
        shipping = float(request.form.get('shipping', 0))
        
        total_amount = subtotal - discount_amount + tax_amount + shipping
        
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{Sale.query.count() + 1:04d}"
        
        sale = Sale(
            invoice_number=invoice_number,
            sale_type=sale_type,
            customer_id=int(customer_id) if customer_id else None,
            subtotal=subtotal,
            discount_type=discount_type,
            discount_value=discount_value,
            discount_amount=discount_amount,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            shipping_charge=shipping,
            total_amount=total_amount,
            payment_method=payment_method,
            payment_status='paid' if payment_method != 'due' else 'pending',
            amount_paid=total_amount if payment_method != 'due' else 0,
            due_amount=total_amount if payment_method == 'due' else 0,
            created_by=current_user.id,
            notes=request.form.get('notes')
        )
        
        db.session.add(sale)
        db.session.flush()
        
        # ✅ Sale Items
        for item in sale_items:
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                cost_price=Product.query.get(item['product_id']).purchase_price,
                total_price=item['total_price'],
                is_product=item['is_product']
            )
            db.session.add(sale_item)
        
        # ✅ Customer Due
        if payment_method == 'due' and customer_id:
            customer_due = CustomerDue(
                customer_id=int(customer_id),
                sale_id=sale.id,
                amount=total_amount,
                due_date=datetime.now() + timedelta(days=30),
                remaining_amount=total_amount,
                status='pending'
            )
            db.session.add(customer_due)
            
            customer = Customer.query.get(int(customer_id))
            if customer:
                customer.total_due += total_amount
        
        # ✅ Customer update
        if customer_id:
            customer = Customer.query.get(int(customer_id))
            if customer:
                customer.total_purchases += total_amount
                customer.total_visits += 1
                customer.last_purchase = datetime.utcnow()
        
        # ✅ Audit Log
        log = AuditLog(
            user_id=current_user.id,
            action='create',
            table_name='sales',
            record_id=sale.id,
            new_values=json.dumps({'invoice': invoice_number, 'total': total_amount}),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        
        db.session.commit()

        customer_name = sale.customer.name if sale.customer else 'Walk-in'
        create_sale_notification(sale.id, customer_name, sale.total_amount)
        
        for item in sale_items:
            product = Product.query.get(item['product_id'])
            if product.stock_quantity <= product.min_stock_level:
                create_low_stock_notification(product.name, product.stock_quantity)
        
        db.session.commit()
        
        flash(f'Sale completed successfully! Invoice: {invoice_number}', 'success')
        return redirect(url_for('view_sale', sale_id=sale.id))
    
    products = Product.query.filter(Product.stock_quantity > 0, Product.is_active == True).all()
    customers = Customer.query.filter_by(is_active=True).all()
    return render_template('new_sale.html', products=products, customers=customers)

@app.route('/sale/<int:sale_id>')
@login_required
def view_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return render_template('view_sale.html', sale=sale)

@app.route('/sale/<int:sale_id>/receipt')
@login_required
def sale_receipt(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return render_template('sale_receipt.html', sale=sale)

# ---------- PDF & WHATSAPP ROUTES ----------

@app.route('/sale/<int:sale_id>/pdf')
@login_required
def sale_pdf(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2563EB'),
            alignment=1,
            spaceAfter=5
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading4'],
            fontSize=12,
            textColor=colors.HexColor('#666666'),
            alignment=1,
            spaceAfter=10
        )
        
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#888888'),
            alignment=1,
            spaceAfter=2
        )
        
        story.append(Paragraph("PRIMEACCESS", title_style))
        story.append(Paragraph("Premium Mobile Accessories", subtitle_style))
        story.append(Paragraph("Data Nagar, Lahore | 📞 0325-7230326", header_style))
        story.append(Spacer(1, 8*mm))
        
        info_data = []
        info_data.append(["Invoice #", sale.invoice_number])
        info_data.append(["Date", sale.created_at.strftime('%d/%m/%Y %I:%M %p')])
        info_data.append(["Customer", sale.customer.name if sale.customer else 'Walk-in Customer'])
        info_data.append(["Payment", sale.payment_method.title() if sale.payment_method else 'N/A'])
        info_data.append(["Status", sale.payment_status.title()])
        
        info_table = Table(info_data, colWidths=[80, 200])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f4fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 8*mm))
        
        item_data = []
        item_data.append(["Item", "Qty", "Price", "Total"])
        
        for item in sale.items:
            name = item.product.name if item.is_product else item.service_name
            if len(name) > 40:
                name = name[:37] + "..."
            item_data.append([
                name,
                str(item.quantity),
                f"PKR {item.unit_price:,.0f}",
                f"PKR {item.total_price:,.0f}"
            ])
        
        item_data.append(["", "", "Subtotal:", f"PKR {sale.subtotal:,.0f}"])
        if sale.discount_amount > 0:
            item_data.append(["", "", "Discount:", f"-PKR {sale.discount_amount:,.0f}"])
        if sale.tax_amount > 0:
            item_data.append(["", "", "Tax:", f"PKR {sale.tax_amount:,.0f}"])
        if sale.shipping_charge > 0:
            item_data.append(["", "", "Shipping:", f"PKR {sale.shipping_charge:,.0f}"])
        item_data.append(["", "", "TOTAL:", f"PKR {sale.total_amount:,.0f}"])
        
        item_table = Table(item_data, colWidths=[200, 50, 80, 80])
        item_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#e0e0e0')),
            ('GRID', (0, -1), (-1, -1), 1, colors.HexColor('#2563EB')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f4fa')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('SPAN', (0, len(item_data)-1), (2, len(item_data)-1)),
        ]))
        story.append(item_table)
        story.append(Spacer(1, 10*mm))
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            alignment=1,
            fontSize=10,
            textColor=colors.grey,
            spaceBefore=5
        )
        
        thanks_style = ParagraphStyle(
            'Thanks',
            parent=styles['Normal'],
            alignment=1,
            fontSize=14,
            textColor=colors.HexColor('#1A2332'),
            spaceBefore=5,
            spaceAfter=5
        )
        
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0')))
        story.append(Paragraph("✨ Thank you for shopping with us! ✨", thanks_style))
        story.append(Paragraph("Returns accepted within 7 days with original receipt", footer_style))
        story.append(Paragraph("Prime Access - The Name of Trust", footer_style))
        
        doc.build(story)
        
        pdf = buffer.getvalue()
        buffer.close()
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Invoice_{sale.invoice_number}.pdf'
        return response
        
    except Exception as e:
        print(f"PDF Error: {str(e)}")
        flash(f'PDF generation error: {str(e)}', 'danger')
        return redirect(url_for('sale_receipt', sale_id=sale_id))

@app.route('/sale/<int:sale_id>/whatsapp', methods=['GET'])
@login_required
def sale_whatsapp(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    
    customer_name = sale.customer.name if sale.customer else 'Walk-in Customer'
    customer_phone = sale.customer.phone if sale.customer and sale.customer.phone else ''
    
    if customer_phone:
        phone = ''.join(filter(str.isdigit, customer_phone))
        if phone.startswith('0'):
            phone = phone[1:]
        if not phone.startswith('92'):
            phone = '92' + phone
    else:
        phone = ''
    
    message = f"""🧾 *PRIMEACCESS* - Invoice

📋 Invoice: {sale.invoice_number}
👤 Customer: {customer_name}
💰 Total: PKR {sale.total_amount:,.0f}
📅 Date: {sale.created_at.strftime('%d/%m/%Y %I:%M %p')}

Thank you for shopping!
📞 0325-7230326
📍 Data Nagar, Lahore"""
    
    if phone and len(phone) >= 10:
        whatsapp_url = f'https://wa.me/{phone}?text={quote(message)}'
    else:
        whatsapp_url = f'https://wa.me/?text={quote(message)}'
    
    return jsonify({
        'success': True,
        'whatsapp_url': whatsapp_url,
        'message': message,
        'invoice': sale.invoice_number,
        'amount': sale.total_amount
    })

@app.route('/sale/<int:sale_id>/return', methods=['GET', 'POST'])
@login_required
def return_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    
    if request.method == 'POST':
        return_items = request.form.getlist('return_item[]')
        return_quantities = request.form.getlist('return_quantity[]')
        
        for i in range(len(return_items)):
            if return_items[i] and return_quantities[i]:
                sale_item = SaleItem.query.get(int(return_items[i]))
                quantity = int(return_quantities[i])
                
                if sale_item and quantity <= sale_item.quantity:
                    product = Product.query.get(sale_item.product_id)
                    if product:
                        product.stock_quantity += quantity
                        
                        movement = StockMovement(
                            product_id=product.id,
                            movement_type='return',
                            quantity=quantity,
                            previous_stock=product.stock_quantity - quantity,
                            new_stock=product.stock_quantity,
                            notes=f'Return from sale #{sale.invoice_number}',
                            created_by=current_user.id
                        )
                        db.session.add(movement)
                    
                    sale_item.is_returned = True
                    sale_item.returned_quantity = quantity
        
        sale.is_returned = True
        sale.return_reason = request.form.get('return_reason')
        db.session.commit()
        
        flash('Return processed successfully!', 'success')
        return redirect(url_for('view_sale', sale_id=sale.id))
    
    return render_template('return_sale.html', sale=sale)

# ---------- Purchase Routes ----------

@app.route('/purchases')
@login_required
def purchases():
    purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    return render_template('purchases.html', purchases=purchases)

@app.route('/purchase/<int:purchase_id>')
@login_required
def view_purchase(purchase_id):
    """View a single purchase"""
    purchase = Purchase.query.get_or_404(purchase_id)
    return render_template('view_purchase.html', purchase=purchase)

@app.route('/new_purchase', methods=['GET', 'POST'])
@login_required
def new_purchase():
    if request.method == 'POST':
        supplier_id = request.form.get('supplier_id')
        payment_method = request.form.get('payment_method')
        
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        prices = request.form.getlist('price[]')
        
        subtotal = 0
        purchase_items = []
        
        for i in range(len(product_ids)):
            if product_ids[i] and quantities[i]:
                product = Product.query.get(int(product_ids[i]))
                if product:
                    quantity = int(quantities[i])
                    price = float(prices[i]) if prices[i] else product.purchase_price
                    total = quantity * price
                    subtotal += total
                    
                    product.stock_quantity += quantity
                    
                    movement = StockMovement(
                        product_id=product.id,
                        movement_type='purchase',
                        quantity=quantity,
                        previous_stock=product.stock_quantity - quantity,
                        new_stock=product.stock_quantity,
                        notes=f'Purchase order #{request.form.get("purchase_number", "")}',
                        created_by=current_user.id
                    )
                    db.session.add(movement)
                    
                    purchase_items.append({
                        'product_id': product.id,
                        'quantity': quantity,
                        'unit_price': price,
                        'total_price': total
                    })
        
        discount = float(request.form.get('discount', 0))
        shipping = float(request.form.get('shipping', 0))
        tax = float(request.form.get('tax', 0))
        total_amount = subtotal - discount + shipping + tax
        
        purchase_number = f"PUR-{datetime.now().strftime('%Y%m%d')}-{Purchase.query.count() + 1:04d}"
        
        purchase = Purchase(
            purchase_number=purchase_number,
            supplier_id=int(supplier_id) if supplier_id else None,
            subtotal=subtotal,
            discount=discount,
            shipping_charge=shipping,
            tax=tax,
            total_amount=total_amount,
            payment_status='paid' if payment_method != 'due' else 'pending',
            amount_paid=total_amount if payment_method != 'due' else 0,
            due_amount=total_amount if payment_method == 'due' else 0,
            created_by=current_user.id,
            received_at=datetime.utcnow(),
            notes=request.form.get('notes')
        )
        
        db.session.add(purchase)
        db.session.flush()
        
        for item in purchase_items:
            purchase_item = PurchaseItem(
                purchase_id=purchase.id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                total_price=item['total_price'],
                received_quantity=item['quantity']
            )
            db.session.add(purchase_item)
        
        if supplier_id:
            supplier = Supplier.query.get(int(supplier_id))
            if supplier:
                supplier.total_purchases += total_amount
                if payment_method == 'due':
                    supplier.total_due += total_amount
        
        db.session.commit()
        flash(f'Purchase completed successfully! PO: {purchase_number}', 'success')
        return redirect(url_for('purchases'))
    
    suppliers = Supplier.query.filter_by(is_active=True).all()
    products = Product.query.filter_by(is_active=True).all()
    return render_template('new_purchase.html', suppliers=suppliers, products=products)

# ---------- Customer Routes ----------

@app.route('/customers')
@login_required
def customers():
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.created_at.desc()).all()
    return render_template('customers.html', customers=customers)

@app.route('/add_customer', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        customer = Customer(
            name=request.form.get('name'),
            phone=request.form.get('phone'),
            phone_secondary=request.form.get('phone_secondary'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            city=request.form.get('city'),
            country=request.form.get('country', 'Pakistan'),
            customer_type=request.form.get('customer_type', 'regular'),
            discount_rate=float(request.form.get('discount_rate', 0)),
            credit_limit=float(request.form.get('credit_limit')) if request.form.get('credit_limit') else None,
            notes=request.form.get('notes'),
            created_by=current_user.id
        )
        db.session.add(customer)
        db.session.commit()
        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers'))
    
    return render_template('add_customer.html')

@app.route('/customer/<int:customer_id>')
@login_required
def view_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    sales = Sale.query.filter_by(customer_id=customer_id).order_by(Sale.created_at.desc()).all()
    dues = CustomerDue.query.filter_by(customer_id=customer_id).all()
    photocopy_jobs = PhotocopyJob.query.filter_by(customer_id=customer_id).order_by(PhotocopyJob.created_at.desc()).all()
    payments = Payment.query.filter_by(customer_id=customer_id).order_by(Payment.payment_date.desc()).all()
    
    return render_template('view_customer.html', 
                         customer=customer, 
                         sales=sales, 
                         dues=dues,
                         photocopy_jobs=photocopy_jobs,
                         payments=payments)

@app.route('/customer/<int:customer_id>/due_payment', methods=['POST'])
@login_required
def customer_due_payment(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    due_id = request.form.get('due_id')
    amount = float(request.form.get('amount'))
    
    if due_id:
        due = CustomerDue.query.get(due_id)
        if due:
            due.paid_amount += amount
            due.remaining_amount = due.amount - due.paid_amount
            if due.remaining_amount <= 0:
                due.status = 'paid'
            else:
                due.status = 'partial'
            due.updated_at = datetime.utcnow()
            
            customer.total_due -= amount
            
            payment = Payment(
                customer_id=customer_id,
                amount=amount,
                payment_method=request.form.get('payment_method'),
                reference_number=request.form.get('reference_number'),
                notes=f'Payment against due #{due.id}',
                created_by=current_user.id
            )
            db.session.add(payment)
            
            db.session.commit()
            create_payment_notification(due.sale_id, customer.name, amount)
            db.session.commit()
            
            flash('Payment recorded successfully!', 'success')
    
    return redirect(url_for('view_customer', customer_id=customer_id))

# ---------- Supplier Routes ----------

@app.route('/suppliers')
@login_required
def suppliers():
    suppliers = Supplier.query.filter_by(is_active=True).all()
    return render_template('suppliers.html', suppliers=suppliers)

@app.route('/add_supplier', methods=['GET', 'POST'])
@login_required
def add_supplier():
    if request.method == 'POST':
        supplier = Supplier(
            name=request.form.get('name'),
            contact_person=request.form.get('contact_person'),
            phone=request.form.get('phone'),
            phone_secondary=request.form.get('phone_secondary'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            shop_name=request.form.get('shop_name'),
            area=request.form.get('area'),
            city=request.form.get('city'),
            country=request.form.get('country', 'Pakistan'),
            credit_limit=float(request.form.get('credit_limit')) if request.form.get('credit_limit') else None,
            payment_terms=request.form.get('payment_terms'),
            notes=request.form.get('notes'),
            created_by=current_user.id
        )
        db.session.add(supplier)
        db.session.commit()
        flash('Supplier added successfully!', 'success')
        return redirect(url_for('suppliers'))
    
    return render_template('add_supplier.html')

@app.route('/supplier/<int:supplier_id>')
@login_required
def view_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    purchases = Purchase.query.filter_by(supplier_id=supplier_id).order_by(Purchase.created_at.desc()).all()
    products = Product.query.filter_by(supplier_id=supplier_id).all()
    payments = Payment.query.filter_by(supplier_id=supplier_id).order_by(Payment.payment_date.desc()).all()
    
    return render_template('view_supplier.html', 
                         supplier=supplier, 
                         purchases=purchases,
                         products=products,
                         payments=payments)

# ---------- Photocopy Routes ----------

@app.route('/photocopy')
@login_required
def photocopy():
    jobs = PhotocopyJob.query.order_by(PhotocopyJob.created_at.desc()).all()
    return render_template('photocopy.html', jobs=jobs)

@app.route('/new_photocopy', methods=['GET', 'POST'])
@login_required
def new_photocopy():
    if request.method == 'POST':
        job_number = f"COPY-{datetime.now().strftime('%Y%m%d')}-{PhotocopyJob.query.count() + 1:04d}"
        
        page_type = request.form.get('page_type')
        total_pages = int(request.form.get('total_pages'))
        rate_per_page = float(request.form.get('rate_per_page'))
        paper_size = request.form.get('paper_size', 'A4')
        copies = int(request.form.get('copies', 1))
        
        actual_pages = total_pages * copies
        total_amount = actual_pages * rate_per_page
        
        paper_stock = PaperStock.query.filter_by(paper_size=paper_size, paper_type=page_type).first()
        if paper_stock and paper_stock.total_sheets - paper_stock.used_sheets >= actual_pages:
            paper_stock.used_sheets += actual_pages
        else:
            flash(f'Insufficient paper stock! Need {actual_pages} sheets, available: {paper_stock.total_sheets - paper_stock.used_sheets if paper_stock else 0}', 'danger')
            return redirect(url_for('new_photocopy'))
        
        job = PhotocopyJob(
            job_number=job_number,
            customer_id=int(request.form.get('customer_id')) if request.form.get('customer_id') else None,
            page_type=page_type,
            page_size=paper_size,
            total_pages=total_pages,
            rate_per_page=rate_per_page,
            total_amount=total_amount,
            paper_used=actual_pages,
            color_type=request.form.get('color_type'),
            double_sided=True if request.form.get('double_sided') else False,
            copies=copies,
            binding=request.form.get('binding'),
            status='completed',
            created_by=current_user.id,
            completed_at=datetime.utcnow(),
            notes=request.form.get('notes')
        )
        
        db.session.add(job)
        db.session.commit()
        
        flash(f'Photocopy job completed! Job #: {job_number}', 'success')
        return redirect(url_for('photocopy'))
    
    customers = Customer.query.filter_by(is_active=True).all()
    paper_stocks = PaperStock.query.all()
    return render_template('new_photocopy.html', customers=customers, paper_stocks=paper_stocks)

@app.route('/photocopy/<int:job_id>')
@login_required
def view_photocopy(job_id):
    job = PhotocopyJob.query.get_or_404(job_id)
    return render_template('view_photocopy.html', job=job)

# ---------- Expense Routes ----------

@app.route('/expenses')
@login_required
def expenses():
    expenses = Expense.query.order_by(Expense.expense_date.desc()).all()
    categories = db.session.query(Expense.category).distinct().all()
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_expenses = Expense.query.filter(
        db.extract('month', Expense.expense_date) == current_month,
        db.extract('year', Expense.expense_date) == current_year
    ).all()
    total_monthly = sum(e.amount for e in monthly_expenses)
    
    return render_template('expenses.html', 
                         expenses=expenses, 
                         categories=categories,
                         total_monthly=total_monthly)

@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        expense = Expense(
            category=request.form.get('category'),
            sub_category=request.form.get('sub_category'),
            description=request.form.get('description'),
            amount=float(request.form.get('amount')),
            expense_date=datetime.strptime(request.form.get('expense_date'), '%Y-%m-%d') if request.form.get('expense_date') else datetime.utcnow(),
            payment_method=request.form.get('payment_method'),
            receipt_number=request.form.get('receipt_number'),
            vendor=request.form.get('vendor'),
            created_by=current_user.id,
            is_recurring=True if request.form.get('is_recurring') else False,
            recurrence_interval=request.form.get('recurrence_interval')
        )
        db.session.add(expense)
        db.session.commit()
        create_notification(
            user_id=None,
            title="💰 New Expense Recorded",
            message=f"{expense.category}: PKR {expense.amount:,.0f} - {expense.description}",
            type='payment',
            link='/expenses'
        )
        db.session.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('expenses'))
    
    categories = ['Rent', 'Electricity', 'Water', 'Internet', 'Salaries', 
                  'Maintenance', 'Stationery', 'Transport', 'Marketing', 'Other']
    return render_template('add_expense.html', categories=categories)

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    """Delete an expense"""
    expense = Expense.query.get_or_404(expense_id)
    
    # Log the deletion
    log = AuditLog(
        user_id=current_user.id,
        action='DELETE',
        table_name='expenses',
        record_id=expense.id,
        old_values=json.dumps({
            'category': expense.category,
            'amount': expense.amount,
            'description': expense.description
        }),
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(log)
    
    db.session.delete(expense)
    db.session.commit()
    
    flash('Expense deleted successfully!', 'success')
    return jsonify({'status': 'success', 'message': 'Expense deleted'})

# ---------- Reports Routes ----------

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

# ============ REPORTS ROUTES - POSTGRESQL COMPATIBLE ============

from sqlalchemy import extract, func, and_, or_
from datetime import datetime, timedelta

# ============ REPORTS SALES ROUTE - COMPLETE ============

@app.route('/reports/sales')
@login_required
def reports_sales():
    """Complete Sales Report with all revenue sources including Bill Payment"""
    try:
        # ============ 1. PRODUCT SALES (Monthly) ============
        product_sales_data = db.session.query(
            func.to_char(Sale.created_at, 'YYYY-MM').label('month'),
            func.sum(Sale.total_amount).label('total_sales'),
            func.count(Sale.id).label('total_orders')
        ).group_by(
            func.to_char(Sale.created_at, 'YYYY-MM')
        ).order_by(
            func.to_char(Sale.created_at, 'YYYY-MM')
        ).all()
        
        # ============ 2. PHOTOCOPY REVENUE (Monthly) ============
        photocopy_data = db.session.query(
            func.to_char(PhotocopyJob.created_at, 'YYYY-MM').label('month'),
            func.sum(PhotocopyJob.total_amount).label('total_photocopy'),
            func.count(PhotocopyJob.id).label('total_jobs')
        ).group_by(
            func.to_char(PhotocopyJob.created_at, 'YYYY-MM')
        ).order_by(
            func.to_char(PhotocopyJob.created_at, 'YYYY-MM')
        ).all()
        
        # ============ 3. WALLET REVENUE (Monthly - Receive only) ============
        wallet_data = db.session.query(
            func.to_char(MobileWalletTransaction.created_at, 'YYYY-MM').label('month'),
            func.sum(MobileWalletTransaction.amount).label('total_wallet'),
            func.count(MobileWalletTransaction.id).label('total_wallet_txns')
        ).filter(
            MobileWalletTransaction.transaction_type == 'receive'
        ).group_by(
            func.to_char(MobileWalletTransaction.created_at, 'YYYY-MM')
        ).order_by(
            func.to_char(MobileWalletTransaction.created_at, 'YYYY-MM')
        ).all()
        
        # ============ 4. WALLET PROFIT (Monthly) ============
        wallet_profit_data = db.session.query(
            func.to_char(MobileWalletTransaction.created_at, 'YYYY-MM').label('month'),
            func.sum(MobileWalletTransaction.amount).label('total_amount'),
            MobileWalletTransaction.transaction_type
        ).group_by(
            func.to_char(MobileWalletTransaction.created_at, 'YYYY-MM'),
            MobileWalletTransaction.transaction_type
        ).order_by(
            func.to_char(MobileWalletTransaction.created_at, 'YYYY-MM')
        ).all()
        
        # ============ 🆕 5. BILL PAYMENT PROFIT (Monthly) ============
        bill_data = db.session.query(
            func.to_char(BillPayment.created_at, 'YYYY-MM').label('month'),
            func.sum(BillPayment.profit_amount).label('total_bill_profit'),
            func.count(BillPayment.id).label('total_bills')
        ).group_by(
            func.to_char(BillPayment.created_at, 'YYYY-MM')
        ).order_by(
            func.to_char(BillPayment.created_at, 'YYYY-MM')
        ).all()
        
        # ============ 6. COMBINE ALL DATA ============
        # Get all unique months
        all_months = set()
        for data in product_sales_data:
            all_months.add(data.month)
        for data in photocopy_data:
            all_months.add(data.month)
        for data in wallet_data:
            all_months.add(data.month)
        for data in bill_data:
            all_months.add(data.month)
        
        # Create combined data
        sales_data = []
        total_product_sales = 0
        total_photocopy_revenue = 0
        total_wallet_revenue = 0
        total_bill_profit = 0
        total_orders = 0
        total_jobs = 0
        total_bills_count = 0
        
        for month in sorted(all_months):
            # Product sales for this month
            product = next((d for d in product_sales_data if d.month == month), None)
            product_amount = float(product.total_sales) if product else 0
            product_orders = product.total_orders if product else 0
            
            # Photocopy for this month
            copy = next((d for d in photocopy_data if d.month == month), None)
            copy_amount = float(copy.total_photocopy) if copy else 0
            copy_jobs = copy.total_jobs if copy else 0
            
            # Wallet for this month
            wallet = next((d for d in wallet_data if d.month == month), None)
            wallet_amount = float(wallet.total_wallet) if wallet else 0
            wallet_txns = wallet.total_wallet_txns if wallet else 0
            
            # Wallet profit for this month
            month_wallet_profit = 0
            for wd in wallet_profit_data:
                if wd.month == month:
                    if wd.transaction_type == 'send':
                        month_wallet_profit += float(wd.total_amount) * 0.01
                    else:
                        month_wallet_profit += float(wd.total_amount) * 0.02
            
            # 🆕 Bill profit for this month
            bill = next((d for d in bill_data if d.month == month), None)
            bill_profit_amount = float(bill.total_bill_profit) if bill else 0
            bill_count = bill.total_bills if bill else 0
            
            # Monthly totals
            monthly_total = product_amount + copy_amount + wallet_amount + bill_profit_amount
            
            sales_data.append({
                'month': month,
                'product_sales': product_amount,
                'photocopy_revenue': copy_amount,
                'wallet_revenue': wallet_amount,
                'wallet_profit': month_wallet_profit,
                'bill_profit': bill_profit_amount,  # 🆕
                'total_revenue': monthly_total,
                'orders': product_orders,
                'jobs': copy_jobs,
                'wallet_txns': wallet_txns,
                'bills': bill_count  # 🆕
            })
            
            # Grand totals
            total_product_sales += product_amount
            total_photocopy_revenue += copy_amount
            total_wallet_revenue += wallet_amount
            total_bill_profit += bill_profit_amount
            total_orders += product_orders
            total_jobs += copy_jobs
            total_bills_count += bill_count
        
        # ============ 7. GRAND TOTALS ============
        total_revenue_all = total_product_sales + total_photocopy_revenue + total_wallet_revenue + total_bill_profit
        
        # Wallet profit (overall)
        total_wallet_send = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
            MobileWalletTransaction.transaction_type == 'send'
        ).scalar() or 0
        
        total_wallet_receive = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
            MobileWalletTransaction.transaction_type == 'receive'
        ).scalar() or 0
        
        total_wallet_profit = (total_wallet_send * 0.01) + (total_wallet_receive * 0.02)
        
        # 🆕 Total bill profit (overall)
        total_bill_profit_overall = db.session.query(func.sum(BillPayment.profit_amount)).scalar() or 0
        
        # ============ 8. RENDER ============
        return render_template('reports_sales.html', 
                             sales_data=sales_data,
                             total_product_sales=total_product_sales,
                             total_photocopy_revenue=total_photocopy_revenue,
                             total_wallet_revenue=total_wallet_revenue,
                             total_bill_profit=total_bill_profit,  # 🆕
                             total_revenue_all=total_revenue_all,
                             total_orders=total_orders,
                             total_jobs=total_jobs,
                             total_wallet_profit=total_wallet_profit,
                             total_bills_count=total_bills_count,  # 🆕
                             total_bill_profit_overall=total_bill_profit_overall)  # 🆕
                             
    except Exception as e:
        print(f"Sales Report Error: {str(e)}")
        flash(f'Error loading sales report: {str(e)}', 'danger')
        return render_template('reports_sales.html', 
                             sales_data=[], 
                             total_product_sales=0,
                             total_photocopy_revenue=0,
                             total_wallet_revenue=0,
                             total_bill_profit=0,
                             total_revenue_all=0,
                             total_orders=0,
                             total_jobs=0,
                             total_wallet_profit=0,
                             total_bills_count=0,
                             total_bill_profit_overall=0)

@app.route('/reports/profit')
@login_required
def reports_profit():
    try:
        # Total revenue
        total_revenue = db.session.query(func.sum(Sale.total_amount)).scalar() or 0
        
        # Total cost from sale items
        total_cost = db.session.query(
            func.sum(SaleItem.cost_price * SaleItem.quantity)
        ).scalar() or 0
        
        # Total expenses
        total_expenses = db.session.query(func.sum(Expense.amount)).scalar() or 0
        
        gross_profit = total_revenue - total_cost
        net_profit = gross_profit - total_expenses
        
        # Monthly breakdown - PostgreSQL compatible
        try:
            monthly_data_raw = db.session.query(
                func.to_char(Sale.created_at, 'YYYY-MM').label('month'),
                func.sum(Sale.total_amount).label('revenue'),
                func.sum(SaleItem.cost_price * SaleItem.quantity).label('cost')
            ).join(SaleItem).group_by(
                func.to_char(Sale.created_at, 'YYYY-MM')
            ).order_by(
                func.to_char(Sale.created_at, 'YYYY-MM')
            ).all()
            
            monthly_data = []
            for data in monthly_data_raw:
                monthly_data.append({
                    'month': data.month,
                    'revenue': float(data.revenue or 0),
                    'cost': float(data.cost or 0)
                })
        except Exception as e:
            print(f"Monthly data error: {str(e)}")
            monthly_data = []
        
        return render_template('reports_profit.html',
                             total_revenue=total_revenue,
                             total_cost=total_cost,
                             total_expenses=total_expenses,
                             gross_profit=gross_profit,
                             net_profit=net_profit,
                             monthly_data=monthly_data)
    except Exception as e:
        print(f"Profit Report Error: {str(e)}")
        return render_template('reports_profit.html',
                             total_revenue=0, 
                             total_cost=0, 
                             total_expenses=0,
                             gross_profit=0, 
                             net_profit=0, 
                             monthly_data=[])

@app.route('/reports/inventory')
@login_required
def reports_inventory():
    try:
        products = Product.query.filter_by(is_active=True).all()
        total_items = len(products)
        total_value = sum((p.purchase_price or 0) * (p.stock_quantity or 0) for p in products)
        
        low_stock_count = Product.query.filter(
            Product.stock_quantity <= Product.min_stock_level,
            Product.stock_quantity > 0,
            Product.is_active == True
        ).count()
        
        out_of_stock_count = Product.query.filter(
            Product.stock_quantity == 0,
            Product.is_active == True
        ).count()
        
        # Category breakdown
        categories_raw = db.session.query(
            Product.category,
            func.sum(Product.stock_quantity).label('total_quantity'),
            func.sum(Product.purchase_price * Product.stock_quantity).label('total_value'),
            func.count(Product.id).label('item_count')
        ).filter(Product.is_active == True).group_by(Product.category).all()
        
        categories = []
        for cat in categories_raw:
            categories.append({
                'category': cat.category or 'Uncategorized',
                'total_quantity': cat.total_quantity or 0,
                'total_value': float(cat.total_value or 0),
                'item_count': cat.item_count or 0
            })
        
        return render_template('reports_inventory.html',
                             products=products,
                             total_items=total_items,
                             total_value=total_value,
                             low_stock_count=low_stock_count,
                             out_of_stock_count=out_of_stock_count,
                             categories=categories)
    except Exception as e:
        print(f"Inventory Report Error: {str(e)}")
        return render_template('reports_inventory.html',
                             products=[], 
                             total_items=0, 
                             total_value=0,
                             low_stock_count=0, 
                             out_of_stock_count=0, 
                             categories=[])

# ============ 🆕 BACKUP ROUTES - UPDATED WITH SUPABASE STORAGE ============

@app.route('/backup', methods=['GET', 'POST'])
@login_required
def backup():
    """Create and manage backups using Supabase Storage"""
    if request.method == 'POST':
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"backup_{timestamp}.json"
            
            # For Supabase PostgreSQL - Export data as JSON
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            backup_data = {}
            for table in tables:
                if table.startswith('sqlite_'):
                    continue
                try:
                    result = db.session.execute(f'SELECT * FROM {table}').fetchall()
                    
                    # ✅ FIXED: Better row to dict conversion
                    if result:
                        # Get column names from result
                        columns = result[0].keys()
                        backup_data[table] = [dict(zip(columns, row)) for row in result]
                    else:
                        backup_data[table] = []
                        
                except Exception as e:
                    print(f"Error backing up table {table}: {str(e)}")
                    backup_data[table] = []
            
            # ✅ FIXED: Better JSON serialization
            def json_serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                if hasattr(obj, '__dict__'):
                    return str(obj)
                return str(obj)
            
            json_data = json.dumps(backup_data, default=json_serializer, indent=2).encode('utf-8')
            
            # Upload to Supabase Storage
            success = upload_to_supabase_storage(json_data, backup_filename)
            
            if not success:
                flash('❌ Failed to upload backup to storage!', 'danger')
                return redirect(url_for('backup'))
            
            # Save backup record in database
            backup = Backup(
                filename=backup_filename,
                size=len(json_data),
                type='manual',
                created_by=current_user.id,
                notes=f'Manual backup by {current_user.username}'
            )
            db.session.add(backup)
            db.session.commit()
            
            flash(f'✅ Backup created successfully! {len(tables)} tables exported.', 'success')
            
        except Exception as e:
            print(f"Backup Error: {str(e)}")
            flash(f'❌ Error creating backup: {str(e)}', 'danger')
        
        return redirect(url_for('backup'))
    
    backups = Backup.query.order_by(Backup.backup_date.desc()).all()
    return render_template('backup.html', backups=backups)


@app.route('/backup/download/<int:backup_id>')
@login_required
def download_backup(backup_id):
    """Download backup file from Supabase Storage"""
    backup = Backup.query.get_or_404(backup_id)
    
    # Download from Supabase Storage
    file_data = download_from_supabase_storage(backup.filename)
    
    if file_data:
        return send_file(
            file_data,
            as_attachment=True,
            download_name=backup.filename,
            mimetype='application/json'
        )
    else:
        flash('❌ Backup file not found in storage.', 'danger')
        return redirect(url_for('backup'))


@app.route('/backup/export_excel/<int:backup_id>')
@login_required
def export_backup_excel(backup_id):
    """Export backup to Excel - Only important tables"""
    backup = Backup.query.get_or_404(backup_id)
    
    try:
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            exported_count = 0
            
            for table in USEFUL_TABLES:
                try:
                    # Check if table exists
                    inspector = inspect(db.engine)
                    if table not in inspector.get_table_names():
                        continue
                    
                    query = f'SELECT * FROM {table}'
                    df = pd.read_sql(query, db.engine)
                    
                    # Skip empty tables
                    if df.empty:
                        continue
                    
                    # Write to Excel
                    sheet_name = table[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Auto-adjust column widths
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                    
                    exported_count += 1
                    print(f"✅ Exported: {table}")
                    
                except Exception as e:
                    print(f"❌ Error exporting {table}: {str(e)}")
                    continue
            
            # If no tables exported, show message
            if exported_count == 0:
                pd.DataFrame({'Message': ['No data found in any table']}).to_excel(
                    writer, sheet_name='No Data', index=False
                )
        
        output.seek(0)
        
        filename = f"backup_{backup.backup_date.strftime('%Y%m%d_%H%M')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Export Error: {str(e)}")
        flash(f'❌ Error exporting backup: {str(e)}', 'danger')
        return redirect(url_for('backup'))


@app.route('/api/backup/filter', methods=['POST'])
@login_required
def filter_backups():
    """Filter backups by date"""
    data = request.json
    filter_type = data.get('filter_type', 'all')
    date_from = data.get('date_from')
    date_to = data.get('date_to')
    
    query = Backup.query
    
    if filter_type == 'today':
        today = datetime.now().date()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
        query = query.filter(Backup.backup_date.between(start, end))
        
    elif filter_type == 'week':
        today = datetime.now().date()
        start = today - timedelta(days=today.weekday())
        start = datetime.combine(start, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
        query = query.filter(Backup.backup_date.between(start, end))
        
    elif filter_type == 'month':
        today = datetime.now().date()
        start = today.replace(day=1)
        start = datetime.combine(start, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
        query = query.filter(Backup.backup_date.between(start, end))
        
    elif filter_type == 'custom':
        if date_from:
            start = datetime.strptime(date_from, '%Y-%m-%d')
            start = datetime.combine(start.date(), datetime.min.time())
            query = query.filter(Backup.backup_date >= start)
        if date_to:
            end = datetime.strptime(date_to, '%Y-%m-%d')
            end = datetime.combine(end.date(), datetime.max.time())
            query = query.filter(Backup.backup_date <= end)
    
    backups = query.order_by(Backup.backup_date.desc()).all()
    
    result = [{
        'id': b.id,
        'filename': b.filename,
        'backup_date': b.backup_date.strftime('%Y-%m-%d %H:%M'),
        'size': b.size,
        'size_kb': round(b.size / 1024, 1) if b.size else 0,
        'type': b.type or 'manual',
        'created_by': current_user.username if b.created_by else 'System'
    } for b in backups]
    
    return jsonify({
        'status': 'success',
        'count': len(result),
        'backups': result
    })


@app.route('/api/backup/delete/<int:backup_id>', methods=['DELETE'])
@login_required
def delete_backup_api(backup_id):
    """Delete backup from Supabase Storage and database"""
    try:
        backup = Backup.query.get_or_404(backup_id)
        
        # Delete from Supabase Storage
        delete_from_supabase_storage(backup.filename)
        
        # Delete record from database
        db.session.delete(backup)
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'message': 'Backup deleted successfully'
        })
    except Exception as e:
        print(f"Delete Error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/color-theme/<theme>')
@login_required
def api_color_theme(theme):
    """Save color theme preference"""
    valid_themes = ['default', 'purple', 'slate', 'white', 'black', 
                    'emerald', 'ocean', 'sunset', 'rose', 'amber',
                    'indigo', 'teal', 'lavender', 'coral', 'cyber']
    
    if theme in valid_themes:
        session['color_theme'] = theme
        return jsonify({'status': 'success', 'theme': theme})
    return jsonify({'status': 'error', 'message': 'Invalid theme'}), 400

@app.route('/api/theme-mode/<mode>')
@login_required
def api_theme_mode(mode):
    """Save theme mode preference"""
    valid_modes = ['light', 'dark', 'auto', 'light-sensor']
    
    if mode in valid_modes:
        session['theme_mode'] = mode
        session['theme'] = mode
        
        # Check if theme_preference column exists before setting
        try:
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            if 'theme_preference' in columns:
                current_user.theme_preference = mode
        except Exception as e:
            print(f"Theme column check error: {e}")
            # Column might not exist yet, ignore
        
        db.session.commit()
        return jsonify({'status': 'success', 'mode': mode})
    
    return jsonify({'status': 'error', 'message': 'Invalid mode'}), 400

@app.route('/api/theme/preference', methods=['GET'])
@login_required
def get_theme_preference():
    """Get user's theme preference"""
    try:
        # Check if column exists
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'theme_preference' in columns:
            theme_mode = current_user.theme_preference or 'auto'
        else:
            theme_mode = 'auto'
    except:
        theme_mode = 'auto'
    
    return jsonify({
        'status': 'success',
        'theme_mode': theme_mode
    })
# ============ REPAIR REVENUE ROUTES ============

@app.route('/repair_revenue')
@login_required
def repair_revenue():
    """Repair Revenue page"""
    repairs = RepairRevenue.query.order_by(RepairRevenue.created_at.desc()).all()
    total_profit = db.session.query(func.sum(RepairRevenue.profit)).scalar() or 0
    return render_template('repair_revenue.html', repairs=repairs, total_profit=total_profit)


@app.route('/repair/add', methods=['POST'])
@login_required
def add_repair():
    """Add new repair"""
    customer_name = request.form.get('customer_name')
    phone = request.form.get('phone')
    device = request.form.get('device')
    issue = request.form.get('issue')
    customer_amount = float(request.form.get('customer_amount'))
    parts_cost = float(request.form.get('parts_cost'))
    status = request.form.get('status', 'pending')
    notes = request.form.get('notes')
    
    profit = customer_amount - parts_cost
    
    repair = RepairRevenue(
        customer_name=customer_name,
        phone=phone,
        device=device,
        issue=issue,
        customer_amount=customer_amount,
        parts_cost=parts_cost,
        profit=profit,
        status=status,
        notes=notes,
        created_by=current_user.id
    )
    
    db.session.add(repair)
    db.session.commit()
    
    create_notification(
        user_id=None,
        title="🔧 New Repair Added!",
        message=f"{customer_name} - {device} repair. Profit: PKR {profit:,.0f}",
        type='sale',
        link='/repair_revenue'
    )
    db.session.commit()
    
    flash(f'✅ Repair added! Profit: PKR {profit:,.0f}', 'success')
    return redirect(url_for('repair_revenue'))


@app.route('/repair/<int:repair_id>/edit', methods=['GET'])
@login_required
def edit_repair(repair_id):
    """Get repair data for editing"""
    repair = RepairRevenue.query.get_or_404(repair_id)
    return jsonify({
        'status': 'success',
        'id': repair.id,
        'customer_name': repair.customer_name,
        'phone': repair.phone,
        'device': repair.device,
        'issue': repair.issue,
        'customer_amount': repair.customer_amount,
        'parts_cost': repair.parts_cost,
        'status': repair.status,
        'notes': repair.notes
    })


@app.route('/repair/<int:repair_id>/update', methods=['POST'])
@login_required
def update_repair(repair_id):
    """Update repair"""
    repair = RepairRevenue.query.get_or_404(repair_id)
    
    repair.customer_name = request.form.get('customer_name')
    repair.phone = request.form.get('phone')
    repair.device = request.form.get('device')
    repair.issue = request.form.get('issue')
    repair.customer_amount = float(request.form.get('customer_amount'))
    repair.parts_cost = float(request.form.get('parts_cost'))
    repair.profit = repair.customer_amount - repair.parts_cost
    repair.status = request.form.get('status')
    repair.notes = request.form.get('notes')
    repair.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('✅ Repair updated successfully!', 'success')
    return redirect(url_for('repair_revenue'))


@app.route('/repair/<int:repair_id>/delete', methods=['POST'])
@login_required
def delete_repair(repair_id):
    """Delete repair"""
    repair = RepairRevenue.query.get_or_404(repair_id)
    db.session.delete(repair)
    db.session.commit()
    return jsonify({'status': 'success'})


# ============ OTHER REVENUE ROUTES ============

@app.route('/other_revenue')
@login_required
def other_revenue():
    """Other Revenue page"""
    revenues = OtherRevenue.query.order_by(OtherRevenue.created_at.desc()).all()
    total_other_revenue = db.session.query(func.sum(OtherRevenue.amount)).scalar() or 0
    return render_template('other_revenue.html', revenues=revenues, total_other_revenue=total_other_revenue)


@app.route('/other_revenue/add', methods=['POST'])
@login_required
def add_other_revenue():
    """Add other revenue"""
    description = request.form.get('description')
    amount = float(request.form.get('amount'))
    category = request.form.get('category', 'other')
    customer_name = request.form.get('customer_name')
    
    revenue = OtherRevenue(
        description=description,
        amount=amount,
        category=category,
        customer_name=customer_name,
        created_by=current_user.id
    )
    
    db.session.add(revenue)
    db.session.commit()
    
    create_notification(
        user_id=None,
        title="💵 New Other Revenue!",
        message=f"{description} - PKR {amount:,.0f}",
        type='payment',
        link='/other_revenue'
    )
    db.session.commit()
    
    flash(f'✅ Other revenue added: {description} - PKR {amount:,.0f}', 'success')
    return redirect(url_for('other_revenue'))


@app.route('/other_revenue/delete/<int:revenue_id>', methods=['POST'])
@login_required
def delete_other_revenue(revenue_id):
    """Delete other revenue"""
    revenue = OtherRevenue.query.get_or_404(revenue_id)
    db.session.delete(revenue)
    db.session.commit()
    return jsonify({'status': 'success'})
# ---------- Settings Routes ----------

@app.route('/settings')
@login_required
def settings():
    users = User.query.all()
    settings = {
        'shop_name': session.get('shop_name', 'PRIMEACCESS'),
        'shop_address': session.get('shop_address', 'Data Nagar, Lahore'),
        'shop_phone': session.get('shop_phone', '0325-7230326'),
        'shop_email': session.get('shop_email', 'info@primeaccess.com'),
        'gst_number': session.get('gst_number', 'XX-XXXXXXX-X'),
        'currency': session.get('currency', 'PKR'),
        'date_format': session.get('date_format', 'dd/mm/yyyy'),
        'time_format': session.get('time_format', '12'),
        'language': session.get('language', 'en'),
        'tax_rate': session.get('tax_rate', '0'),
        'discount_rate': session.get('discount_rate', '0'),
        'shipping_charge': session.get('shipping_charge', '0'),
        'footer_text': session.get('footer_text', 'Thank you for shopping with us!'),
        'maintenance_mode': session.get('maintenance_mode', 'false'),
        'invoice_prefix': session.get('invoice_prefix', 'INV-'),
        'next_invoice': session.get('next_invoice', '1001'),
        'logo_position': session.get('logo_position', 'left'),
        'receipt_footer': session.get('receipt_footer', 'Thank you for shopping!'),
        'show_barcode': session.get('show_barcode', 'true'),
        'default_payment': session.get('default_payment', 'cash'),
        'due_days': session.get('due_days', '30'),
        'jazzcash_number': session.get('jazzcash_number', ''),
        'easypaisa_number': session.get('easypaisa_number', ''),
        'bank_account': session.get('bank_account', ''),
        'backup_frequency': session.get('backup_frequency', 'weekly'),
        'backup_time': session.get('backup_time', '02:00'),
        'keep_backups': session.get('keep_backups', '10'),
        'auto_export_excel': session.get('auto_export_excel', 'false')
    }
    return render_template('settings.html', users=users, settings=settings)

@app.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        current_user.email = request.form.get('email')
        
        if request.form.get('password'):
            current_user.set_password(request.form.get('password'))
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('settings') + '#profile')
    
    return render_template('settings_profile.html')

@app.route('/settings/preferences', methods=['POST'])
@login_required
def settings_preferences():
    theme = request.form.get('theme', 'light')
    session['theme'] = theme
    flash('Preferences updated successfully!', 'success')
    return redirect(url_for('settings') + '#theme')

@app.route('/settings/general', methods=['POST'])
@login_required
def settings_general():
    session['shop_name'] = request.form.get('shop_name', 'PRIMEACCESS')
    session['shop_address'] = request.form.get('shop_address', 'Data Nagar, Lahore')
    session['shop_phone'] = request.form.get('shop_phone', '0325-7230326')
    session['shop_email'] = request.form.get('shop_email', 'info@primeaccess.com')
    session['gst_number'] = request.form.get('gst_number', 'XX-XXXXXXX-X')
    session['currency'] = request.form.get('currency', 'PKR')
    session['date_format'] = request.form.get('date_format', 'dd/mm/yyyy')
    session['time_format'] = request.form.get('time_format', '12')
    session['language'] = request.form.get('language', 'en')
    session['tax_rate'] = float(request.form.get('tax_rate', 0))
    session['discount_rate'] = float(request.form.get('discount_rate', 0))
    session['shipping_charge'] = float(request.form.get('shipping_charge', 0))
    session['footer_text'] = request.form.get('footer_text', 'Thank you for shopping with us!')
    session['maintenance_mode'] = 'true' if request.form.get('maintenance_mode') else 'false'
    
    flash('✅ General settings saved successfully!', 'success')
    return redirect(url_for('settings') + '#general')

@app.route('/settings/invoice', methods=['POST'])
@login_required
def settings_invoice():
    session['invoice_prefix'] = request.form.get('invoice_prefix', 'INV-')
    session['next_invoice'] = int(request.form.get('next_invoice', 1001))
    session['logo_position'] = request.form.get('logo_position', 'left')
    session['receipt_footer'] = request.form.get('receipt_footer', 'Thank you for shopping!')
    session['show_barcode'] = 'true' if request.form.get('show_barcode') else 'false'
    
    flash('✅ Invoice settings saved successfully!', 'success')
    return redirect(url_for('settings') + '#invoice')

@app.route('/settings/payments', methods=['POST'])
@login_required
def settings_payments():
    session['default_payment'] = request.form.get('default_payment', 'cash')
    session['due_days'] = int(request.form.get('due_days', 30))
    session['jazzcash_number'] = request.form.get('jazzcash_number', '')
    session['easypaisa_number'] = request.form.get('easypaisa_number', '')
    session['bank_account'] = request.form.get('bank_account', '')
    
    flash('✅ Payment settings saved successfully!', 'success')
    return redirect(url_for('settings') + '#payments')

@app.route('/settings/backup', methods=['POST'])
@login_required
def settings_backup():
    session['backup_frequency'] = request.form.get('backup_frequency', 'weekly')
    session['backup_time'] = request.form.get('backup_time', '02:00')
    session['keep_backups'] = int(request.form.get('keep_backups', 10))
    session['auto_export_excel'] = 'true' if request.form.get('auto_export_excel') else 'false'
    
    flash('✅ Backup settings saved successfully!', 'success')
    return redirect(url_for('settings') + '#backup')

# ---------- Language Routes ----------

@app.route('/set_language/<lang>')
@login_required
def set_language(lang):
    if lang in ['ur', 'en']:
        session['language'] = lang
        if lang == 'ur':
            flash('✅ زبان اردو میں تبدیل ہو گئی', 'success')
        else:
            flash('✅ Language changed to English', 'success')
    else:
        flash('❌ Invalid language selection', 'danger')
    
    referer = request.headers.get('Referer')
    if referer:
        return redirect(referer)
    return redirect(url_for('settings'))

# ---------- Mobile Wallet Routes ----------

@app.route('/mobile_wallet')
@login_required
def mobile_wallet():
    """Mobile Wallet Management - With Profit Calculation"""
    transactions = MobileWalletTransaction.query.order_by(MobileWalletTransaction.created_at.desc()).all()
    
    # ============ JAZZCASH ============
    total_received_jazz = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.wallet_type == 'jazzcash',
        MobileWalletTransaction.transaction_type == 'receive'
    ).scalar() or 0
    
    total_sent_jazz = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.wallet_type == 'jazzcash',
        MobileWalletTransaction.transaction_type == 'send'
    ).scalar() or 0
    
    balance_jazz = total_received_jazz - total_sent_jazz
    
    # ============ EASYPAISA ============
    total_received_easy = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.wallet_type == 'easypaisa',
        MobileWalletTransaction.transaction_type == 'receive'
    ).scalar() or 0
    
    total_sent_easy = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.wallet_type == 'easypaisa',
        MobileWalletTransaction.transaction_type == 'send'
    ).scalar() or 0
    
    balance_easy = total_received_easy - total_sent_easy
    
    # ============ WALLET PROFIT CALCULATION ============
    # Rule: Send = 1% profit, Receive = 2% profit
    
    # Total send transactions (both wallets)
    total_wallet_send = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.transaction_type == 'send'
    ).scalar() or 0
    
    # Total receive transactions (both wallets)
    total_wallet_receive = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.transaction_type == 'receive'
    ).scalar() or 0
    
    # Calculate profit
    # Send: 1% profit (1000 → 10)
    # Receive: 2% profit (1000 → 20)
    wallet_profit = (total_wallet_send * 0.01) + (total_wallet_receive * 0.02)
    
    # Today's wallet profit
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    today_wallet_send = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.created_at.between(today_start, today_end),
        MobileWalletTransaction.transaction_type == 'send'
    ).scalar() or 0
    
    today_wallet_receive = db.session.query(func.sum(MobileWalletTransaction.amount)).filter(
        MobileWalletTransaction.created_at.between(today_start, today_end),
        MobileWalletTransaction.transaction_type == 'receive'
    ).scalar() or 0
    
    today_wallet_profit = (today_wallet_send * 0.01) + (today_wallet_receive * 0.02)
    
    # ============ TODAY'S TRANSACTIONS ============
    today_transactions = MobileWalletTransaction.query.filter(
        MobileWalletTransaction.created_at.between(today_start, today_end)
    ).all()
    
    today_total_received = sum(t.amount for t in today_transactions if t.transaction_type == 'receive')
    today_total_sent = sum(t.amount for t in today_transactions if t.transaction_type == 'send')
    
    # ============ CUSTOMERS ============
    customers = Customer.query.filter_by(is_active=True).all()
    
    return render_template('mobile_wallet.html', 
                         # === TRANSACTIONS ===
                         transactions=transactions,
                         today_transactions=today_transactions,
                         
                         # === JAZZCASH ===
                         total_received_jazz=total_received_jazz,
                         total_sent_jazz=total_sent_jazz,
                         balance_jazz=balance_jazz,
                         
                         # === EASYPAISA ===
                         total_received_easy=total_received_easy,
                         total_sent_easy=total_sent_easy,
                         balance_easy=balance_easy,
                         
                         # === PROFIT ===
                         wallet_profit=wallet_profit,
                         today_wallet_profit=today_wallet_profit,
                         total_wallet_send=total_wallet_send,
                         total_wallet_receive=total_wallet_receive,
                         
                         # === TODAY ===
                         today_total_received=today_total_received,
                         today_total_sent=today_total_sent,
                         
                         # === OTHER ===
                         customers=customers)

@app.route('/mobile_wallet/receipt/<int:transaction_id>')
@login_required
def mobile_wallet_receipt(transaction_id):
    """Print receipt for mobile wallet transaction"""
    transaction = MobileWalletTransaction.query.get_or_404(transaction_id)
    return render_template('mobile_wallet_receipt.html', transaction=transaction)

@app.route('/mobile_wallet/add', methods=['POST'])
@login_required
def add_mobile_wallet():
    """Add new mobile wallet transaction"""
    wallet_type = request.form.get('wallet_type')
    transaction_type = request.form.get('transaction_type')
    customer_id = request.form.get('customer_id')
    amount = float(request.form.get('amount'))
    phone_number = request.form.get('phone_number')
    customer_name = request.form.get('customer_name')
    transaction_id = request.form.get('transaction_id')
    notes = request.form.get('notes')
    
    transaction = MobileWalletTransaction(
        wallet_type=wallet_type,
        transaction_type=transaction_type,
        customer_id=int(customer_id) if customer_id else None,
        amount=amount,
        phone_number=phone_number,
        customer_name=customer_name,
        transaction_id=transaction_id,
        notes=notes,
        created_by=current_user.id
    )
    
    db.session.add(transaction)
    
    # If receive transaction, deduct from customer due
    if transaction_type == 'receive' and customer_id:
        customer = Customer.query.get(int(customer_id))
        if customer:
            customer.total_due -= amount
    
    db.session.commit()
    
    # Calculate profit for this transaction
    if transaction_type == 'send':
        profit = amount * 0.01  # 1%
    else:
        profit = amount * 0.02  # 2%
    
    flash(f'{wallet_type.title()} transaction added! Profit: PKR {profit:,.0f}', 'success')
    return redirect(url_for('mobile_wallet'))

@app.route('/mobile_wallet/delete/<int:transaction_id>', methods=['POST'])
@login_required
def delete_mobile_wallet(transaction_id):
    """Delete mobile wallet transaction"""
    transaction = MobileWalletTransaction.query.get_or_404(transaction_id)
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully!', 'success')
    return jsonify({'status': 'success'})

# ============================================
# NOTIFICATION ROUTES
# ============================================

@app.route('/api/notifications', methods=['GET'])
@login_required
def api_notifications():
    """Get user notifications"""
    limit = request.args.get('limit', 50, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    query = Notification.query.filter(
        (Notification.user_id == current_user.id) | (Notification.user_id.is_(None))
    ).order_by(Notification.created_at.desc())
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    notifications = query.limit(limit).all()
    return jsonify([n.to_dict() for n in notifications])

@app.route('/api/notifications/unread/count', methods=['GET'])
@login_required
def api_notifications_unread_count():
    """Get unread notification count"""
    count = Notification.query.filter(
        (Notification.user_id == current_user.id) | (Notification.user_id.is_(None)),
        Notification.is_read == False
    ).count()
    return jsonify({'count': count})

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def api_notification_read(notification_id):
    """Mark notification as read"""
    notification = Notification.query.get(notification_id)
    if notification and (notification.user_id == current_user.id or notification.user_id is None):
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_notifications_read_all():
    """Mark all notifications as read"""
    notifications = Notification.query.filter(
        (Notification.user_id == current_user.id) | (Notification.user_id.is_(None)),
        Notification.is_read == False
    ).all()
    
    for n in notifications:
        n.is_read = True
        n.read_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True, 'count': len(notifications)})

@app.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
@login_required
def api_notification_delete(notification_id):
    """Delete a notification"""
    notification = Notification.query.get(notification_id)
    if notification and (notification.user_id == current_user.id or notification.user_id is None):
        db.session.delete(notification)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/notifications/clear', methods=['POST'])
@login_required
def api_notifications_clear():
    """Clear all read notifications"""
    notifications = Notification.query.filter(
        (Notification.user_id == current_user.id) | (Notification.user_id.is_(None)),
        Notification.is_read == True
    ).all()
    
    for n in notifications:
        db.session.delete(n)
    
    db.session.commit()
    return jsonify({'success': True, 'count': len(notifications)})


# ============ ACTIVITY LOG PAGE ============

@app.route('/activity_log')
@login_required
def activity_log():
    """Activity Log page"""
    return render_template('activity_log.html')


# ============ ACTIVITY LOG API ============

@app.route('/api/activities')
@login_required
def api_activities():
    """Get all activities for a month"""
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    
    try:
        year, month_num = map(int, month.split('-'))
        month_start = datetime(year, month_num, 1, 0, 0, 0)
        if month_num == 12:
            month_end = datetime(year + 1, 1, 1, 0, 0, 0)
        else:
            month_end = datetime(year, month_num + 1, 1, 0, 0, 0)
        
        activities = []
        
        # ===== 1. SALES =====
        try:
            sales = Sale.query.filter(Sale.created_at.between(month_start, month_end)).all()
            for sale in sales:
                item_count = len(sale.items) if sale.items else 0
                activities.append({
                    'type': 'sale',
                    'customer': sale.customer.name if sale.customer else 'Walk-in',
                    'invoice': sale.invoice_number,
                    'amount': float(sale.total_amount or 0),
                    'description': f'Sale of {item_count} items',
                    'time': sale.created_at.strftime('%d/%m/%Y %I:%M %p'),
                    'details': {
                        'items': item_count,
                        'payment': sale.payment_method,
                        'status': sale.payment_status
                    }
                })
        except Exception as e:
            print(f"Sales error: {str(e)}")
        
        # ===== 2. WALLET TRANSACTIONS =====
        try:
            wallet = MobileWalletTransaction.query.filter(
                MobileWalletTransaction.created_at.between(month_start, month_end)
            ).all()
            for w in wallet:
                profit = float(w.amount or 0) * 0.01 if w.transaction_type == 'send' else float(w.amount or 0) * 0.02
                activities.append({
                    'type': 'wallet',
                    'customer': w.customer.name if w.customer else w.customer_name or 'Unknown',
                    'phone': w.phone_number or '',
                    'amount': profit,
                    'description': f'{w.transaction_type.title()} - {w.wallet_type.title()}',
                    'category': w.wallet_type,
                    'time': w.created_at.strftime('%d/%m/%Y %I:%M %p'),
                    'details': {
                        'transaction_id': w.transaction_id or '',
                        'type': w.transaction_type,
                        'wallet': w.wallet_type
                    }
                })
        except Exception as e:
            print(f"Wallet error: {str(e)}")
        
        # ===== 3. PHOTOCOPY JOBS =====
        try:
            photocopy = PhotocopyJob.query.filter(
                PhotocopyJob.created_at.between(month_start, month_end)
            ).all()
            for p in photocopy:
                activities.append({
                    'type': 'photocopy',
                    'customer': p.customer.name if p.customer else 'Walk-in',
                    'amount': float(p.total_amount or 0),
                    'description': f'{p.total_pages or 0} pages, {p.copies or 1} copies',
                    'category': p.page_type or '',
                    'time': p.created_at.strftime('%d/%m/%Y %I:%M %p'),
                    'details': {
                        'job_number': p.job_number or '',
                        'pages': p.total_pages or 0,
                        'copies': p.copies or 1,
                        'paper_used': p.paper_used or 0
                    }
                })
        except Exception as e:
            print(f"Photocopy error: {str(e)}")
        
        # ===== 4. DATA REVENUE =====
        try:
            # Check if DataRevenue table exists
            inspector = inspect(db.engine)
            if 'data_revenue' in inspector.get_table_names():
                data_revenue = DataRevenue.query.filter(
                    DataRevenue.created_at.between(month_start, month_end)
                ).all()
                for d in data_revenue:
                    activities.append({
                        'type': 'data',
                        'customer': d.customer_name or 'Unknown',
                        'phone': d.phone or '',
                        'amount': float(d.amount or 0),
                        'description': d.description or d.category or '',
                        'category': d.category or '',
                        'time': d.created_at.strftime('%d/%m/%Y %I:%M %p'),
                        'details': {
                            'category': d.category or ''
                        }
                    })
        except Exception as e:
            print(f"Data Revenue error: {str(e)}")
        
        # ===== 🆕 5. BILL PAYMENTS =====
        try:
            inspector = inspect(db.engine)
            if 'bill_payments' in inspector.get_table_names():
                bills = BillPayment.query.filter(
                    BillPayment.created_at.between(month_start, month_end)
                ).all()
                for b in bills:
                    activities.append({
                        'type': 'bill',
                        'customer': b.customer_name or 'Unknown',
                        'phone': b.phone or '',
                        'amount': float(b.profit_amount or 0),  # Sirf profit
                        'bill_amount': float(b.bill_amount or 0),  # Original bill
                        'description': f'{b.bill_type.title()} bill - PKR {b.bill_amount:,.0f}',
                        'category': b.bill_type,
                        'reference': b.reference_number or '',
                        'time': b.created_at.strftime('%d/%m/%Y %I:%M %p'),
                        'details': {
                            'bill_type': b.bill_type,
                            'bill_amount': float(b.bill_amount or 0),
                            'reference': b.reference_number or ''
                        }
                    })
        except Exception as e:
            print(f"Bill payments error: {str(e)}")
        
        # ===== 6. CUSTOMERS =====
        try:
            customers = Customer.query.filter(
                Customer.created_at.between(month_start, month_end)
            ).all()
            for c in customers:
                activities.append({
                    'type': 'customer',
                    'customer': c.name or '',
                    'phone': c.phone or '',
                    'description': 'New customer registered',
                    'time': c.created_at.strftime('%d/%m/%Y %I:%M %p'),
                    'details': {
                        'phone': c.phone or '',
                        'type': c.customer_type or 'regular'
                    }
                })
        except Exception as e:
            print(f"Customers error: {str(e)}")
        
        # ===== 7. PRODUCTS =====
        try:
            products = Product.query.filter(
                Product.created_at.between(month_start, month_end)
            ).all()
            for p in products:
                activities.append({
                    'type': 'product',
                    'product': p.name or '',
                    'category': p.category or '',
                    'description': f'New product added - {p.sku or ""}',
                    'amount': float(p.selling_price or 0),
                    'time': p.created_at.strftime('%d/%m/%Y %I:%M %p'),
                    'details': {
                        'sku': p.sku or '',
                        'category': p.category or '',
                        'stock': p.stock_quantity or 0
                    }
                })
        except Exception as e:
            print(f"Products error: {str(e)}")
        
        # Sort by time (newest first)
        activities.sort(key=lambda x: x.get('time', ''), reverse=True)
        
        # ===== STATS =====
        stats = {
            'total_revenue': sum(a.get('amount', 0) for a in activities if a.get('type') in ['sale', 'photocopy', 'wallet', 'data', 'bill']),
            'total_sales': len([a for a in activities if a.get('type') == 'sale']),
            'total_photocopy': len([a for a in activities if a.get('type') == 'photocopy']),
            'total_wallet': sum(a.get('amount', 0) for a in activities if a.get('type') == 'wallet'),
            'total_data': sum(a.get('amount', 0) for a in activities if a.get('type') == 'data'),
            'total_customers': len([a for a in activities if a.get('type') == 'customer']),
            'total_bills': len([a for a in activities if a.get('type') == 'bill']),  # 🆕
            'total_bill_profit': sum(a.get('amount', 0) for a in activities if a.get('type') == 'bill')  # 🆕
        }
        
        return jsonify({
            'status': 'success',
            'activities': activities,
            'stats': stats,
            'count': len(activities)
        })
        
    except Exception as e:
        print(f"Activity API Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e),
            'activities': [],
            'stats': {}
        }), 500

# ============ DEBUG ROUTE ============

@app.route('/api/debug')
@login_required
def api_debug():
    """Debug endpoint - check database tables"""
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        # Check each table for data
        table_data = {}
        for table in tables:
            try:
                count = db.session.execute(f'SELECT COUNT(*) FROM {table}').scalar()
                table_data[table] = count
            except:
                table_data[table] = 'Error'
        
        return jsonify({
            'status': 'success',
            'tables': tables,
            'table_counts': table_data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ============================================
# NOTIFICATION HELPER FUNCTIONS
# ============================================

def create_notification(user_id, title, message, type='info', link=None):
    """Create a new notification"""
    icons = {
        'info': 'fa-info-circle',
        'success': 'fa-check-circle',
        'warning': 'fa-exclamation-triangle',
        'danger': 'fa-times-circle',
        'sale': 'fa-shopping-cart',
        'stock': 'fa-box',
        'payment': 'fa-money-bill-wave',
        'user': 'fa-user',
        'system': 'fa-server'
    }
    
    colors = {
        'info': '#2563EB',
        'success': '#0D9488',
        'warning': '#D97706',
        'danger': '#E11D48',
        'sale': '#2563EB',
        'stock': '#F59E0B',
        'payment': '#0D9488',
        'user': '#7C3AED',
        'system': '#475569'
    }
    
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        icon=icons.get(type, 'fa-info-circle'),
        color=colors.get(type, '#2563EB'),
        link=link,
        created_at=datetime.utcnow()
    )
    
    db.session.add(notification)
    db.session.commit()
    return notification

def create_sale_notification(sale_id, customer_name, amount):
    """Create notification for new sale"""
    return create_notification(
        user_id=None,
        title="🛒 New Sale!",
        message=f"{customer_name} placed an order of ₨{amount:,.0f}",
        type='sale',
        link=f'/sale/{sale_id}'
    )

def create_low_stock_notification(product_name, current_stock):
    """Create notification for low stock alert"""
    return create_notification(
        user_id=None,
        title="⚠️ Low Stock Alert!",
        message=f"{product_name} has only {current_stock} units left!",
        type='stock',
        link='/products'
    )

def create_payment_notification(invoice_id, customer_name, amount):
    """Create notification for payment received"""
    return create_notification(
        user_id=None,
        title="💰 Payment Received!",
        message=f"Payment of ₨{amount:,.0f} received from {customer_name}",
        type='payment',
        link=f'/sale/{invoice_id}'
    )

# ---------- API Routes ----------

@app.route('/api/search/products')
@login_required
def api_search_products():
    query = request.args.get('q', '')
    products = Product.query.filter(
        or_(
            Product.name.contains(query),
            Product.barcode.contains(query),
            Product.sku.contains(query)
        ),
        Product.is_active == True
    ).limit(20).all()
    
    result = [{
        'id': p.id,
        'name': p.name,
        'barcode': p.barcode,
        'sku': p.sku,
        'selling_price': p.selling_price,
        'stock_quantity': p.stock_quantity,
        'unit': p.unit,
        'category': p.category
    } for p in products]
    
    return jsonify(result)

@app.route('/api/stock/alert')
@login_required
def api_stock_alert():
    low_stock = Product.query.filter(
        Product.stock_quantity <= Product.min_stock_level,
        Product.is_active == True
    ).all()
    
    out_of_stock = Product.query.filter(
        Product.stock_quantity == 0,
        Product.is_active == True
    ).all()
    
    result = {
        'low_stock': [{'name': p.name, 'stock': p.stock_quantity, 'min': p.min_stock_level} for p in low_stock],
        'out_of_stock': [{'name': p.name, 'stock': p.stock_quantity} for p in out_of_stock]
    }
    
    return jsonify(result)

@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    today_sales = Sale.query.filter(Sale.created_at.between(today_start, today_end)).all()
    total_sales_today = sum(sale.total_amount for sale in today_sales)
    total_sales_count = len(today_sales)
    
    low_stock_count = Product.query.filter(
        Product.stock_quantity <= Product.min_stock_level,
        Product.is_active == True
    ).count()
    
    return jsonify({
        'total_sales_today': total_sales_today,
        'total_sales_count': total_sales_count,
        'low_stock_count': low_stock_count
    })

@app.route('/api/theme/<theme>')
@login_required
def api_theme(theme):
    session['theme'] = theme
    return jsonify({'status': 'success', 'theme': theme})

@app.route('/api/recent-activity')
@login_required
def api_recent_activity():
    activities = []
    
    recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(5).all()
    for sale in recent_sales:
        activities.append({
            'type': 'sale',
            'icon': 'cart-plus',
            'text': f'New sale #{sale.invoice_number} by {sale.customer.name if sale.customer else "Walk-in"} - PKR {sale.total_amount:,.0f}',
            'time': sale.created_at.strftime('%I:%M %p')
        })
    
    recent_customers = Customer.query.order_by(Customer.created_at.desc()).limit(3).all()
    for customer in recent_customers:
        activities.append({
            'type': 'customer',
            'icon': 'user-plus',
            'text': f'New customer registered: {customer.name}',
            'time': customer.created_at.strftime('%I:%M %p')
        })
    
    recent_copy = PhotocopyJob.query.order_by(PhotocopyJob.created_at.desc()).limit(3).all()
    for job in recent_copy:
        activities.append({
            'type': 'copy',
            'icon': 'copy',
            'text': f'Photocopy job #{job.job_number} - {job.total_pages} pages',
            'time': job.created_at.strftime('%I:%M %p')
        })
    
    # 🆕 Recent bill payments
    recent_bills = BillPayment.query.order_by(BillPayment.created_at.desc()).limit(3).all()
    for bill in recent_bills:
        activities.append({
            'type': 'bill',
            'icon': 'file-invoice-dollar',
            'text': f'{bill.bill_type.title()} bill - Profit PKR {bill.profit_amount:,.0f}',
            'time': bill.created_at.strftime('%I:%M %p')
        })
    
    activities.sort(key=lambda x: x['time'], reverse=True)
    return jsonify(activities[:10])

@app.route('/api/top-customers')
@login_required
def api_top_customers():
    customers = Customer.query.filter(
        Customer.total_purchases > 0
    ).order_by(Customer.total_purchases.desc()).limit(5).all()
    
    result = [{
        'name': c.name,
        'total_purchases': c.total_visits,
        'total_spent': c.total_purchases
    } for c in customers]
    
    return jsonify(result)

@app.route('/api/notifications/count')
@login_required
def api_notifications_count():
    count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    return jsonify({'count': count})

# ---------- Error Handlers ----------

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

# ---------- Profile Routes ----------

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/profile/update', methods=['POST'])
@login_required
def profile_update():
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    if full_name:
        current_user.full_name = full_name
    
    if email:
        current_user.email = email
    
    if password:
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('profile'))
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('profile'))
        current_user.set_password(password)
    
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

# ==================== PWA ROUTES ====================

@app.route('/manifest.json')
def serve_manifest():
    """Serve manifest.json for PWA"""
    try:
        return send_file('manifest.json', mimetype='application/json')
    except:
        # If file not found, return generated manifest
        return jsonify({
            "name": "PRIMEACCESS Shop",
            "short_name": "PrimeShop",
            "description": "Premium Mobile Accessories & Photocopy Shop",
            "start_url": "/",
            "display": "standalone",
            "orientation": "portrait",
            "scope": "/",
            "background_color": "#2563EB",
            "theme_color": "#2563EB",
            "icons": [
                {
                    "src": "/static/img/logo1.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/static/img/logo1.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable"
                }
            ]
        })

@app.route('/sw.js')
def serve_sw():
    """Serve service worker"""
    try:
        return send_file('sw.js', mimetype='application/javascript')
    except:
        # Generate minimal SW
        sw_code = '''
const CACHE_NAME = 'prime-shop-v3';
const ASSETS = ['/', '/login', '/static/css/style.css', '/static/js/custom.js', '/offline.html'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).catch(() => caches.match('/offline.html'))));
});
        '''
        return Response(sw_code, mimetype='application/javascript')

# ============================================
# OFFLINE SYNC API
# ============================================

@app.route('/api/sync', methods=['POST'])
@login_required
def api_sync():
    """Sync offline data from mobile to server"""
    try:
        data = request.json
        action = data.get('type')
        
        if action == 'sale':
            sale_data = data.get('data', {})
            
            invoice_number = f"SYNC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            sale = Sale(
                invoice_number=invoice_number,
                sale_type=sale_data.get('sale_type', 'retail'),
                customer_id=int(sale_data.get('customer_id')) if sale_data.get('customer_id') else None,
                subtotal=sale_data.get('subtotal', 0),
                discount_type=sale_data.get('discount_type', 'percentage'),
                discount_value=float(sale_data.get('discount_value', 0)),
                discount_amount=0,
                tax_rate=float(sale_data.get('tax_rate', 0)),
                tax_amount=0,
                shipping_charge=float(sale_data.get('shipping', 0)),
                total_amount=sale_data.get('total_amount', 0),
                payment_method=sale_data.get('payment_method', 'cash'),
                payment_status='paid',
                amount_paid=sale_data.get('total_amount', 0),
                due_amount=0,
                created_by=current_user.id,
                notes=f"Synced from mobile: {sale_data.get('notes', '')}"
            )
            db.session.add(sale)
            db.session.flush()
            
            for item in sale_data.get('items', []):
                product_id = item.get('product_id')
                quantity = int(item.get('quantity', 1))
                price = float(item.get('price', 0))
                
                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=price,
                    total_price=price * quantity,
                    is_product=True
                )
                db.session.add(sale_item)
                
                if product_id:
                    product = Product.query.get(product_id)
                    if product:
                        product.stock_quantity -= quantity
                        
                        movement = StockMovement(
                            product_id=product.id,
                            movement_type='sale',
                            quantity=-quantity,
                            previous_stock=product.stock_quantity + quantity,
                            new_stock=product.stock_quantity,
                            notes=f'Sync from mobile: {invoice_number}',
                            created_by=current_user.id
                        )
                        db.session.add(movement)
            
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'Sale synced successfully',
                'invoice': invoice_number
            })
        
        return jsonify({'status': 'error', 'message': 'Unknown action type'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Sync error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
# ============================================
# AI ASSISTANT ROUTES - FULL NATURAL LANGUAGE
# ============================================

@app.route('/ai_assistant')
@login_required
def ai_assistant():
    """AI Assistant Page"""
    return render_template('ai_assistant.html')


@app.route('/api/ai/ask', methods=['POST'])
@login_required
def ai_ask():
    """AI Assistant - Natural Language Processing"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({
                'status': 'error',
                'message': 'Question is required'
            })
        
        # Parse date from question
        date_info = parse_date_from_question(question)
        
        # Get shop data for date range
        shop_data = get_shop_data_for_date_range(date_info)
        
        # Generate intelligent response
        response = generate_intelligent_response(question, shop_data, date_info)
        
        return jsonify({
            'status': 'success',
            'response': response
        })
        
    except Exception as e:
        print(f"AI Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'response': f"Sorry, I encountered an error: {str(e)}"
        }), 500


def parse_date_from_question(question):
    """Parse date from any question - supports natural language"""
    question_lower = question.lower()
    today = datetime.now().date()
    
    # Default: today
    date_info = {
        'type': 'today',
        'start_date': today,
        'end_date': today,
        'display': 'Today'
    }
    
    # ===== TODAY =====
    if any(word in question_lower for word in ['today', 'aj', 'aaj', 'آج', "today's", 'current day']):
        date_info = {'type': 'today', 'start_date': today, 'end_date': today, 'display': 'Today'}
    
    # ===== YESTERDAY =====
    elif any(word in question_lower for word in ['yesterday', 'kal', 'کل', 'previous day']):
        yesterday = today - timedelta(days=1)
        date_info = {'type': 'yesterday', 'start_date': yesterday, 'end_date': yesterday, 'display': 'Yesterday'}
    
    # ===== TOMORROW =====
    elif any(word in question_lower for word in ['tomorrow', 'kal', 'آنے والا کل']):
        tomorrow = today + timedelta(days=1)
        date_info = {'type': 'tomorrow', 'start_date': tomorrow, 'end_date': tomorrow, 'display': 'Tomorrow'}
    
    # ===== THIS WEEK =====
    elif any(word in question_lower for word in ['this week', 'is hafte', 'اس ہفتے', 'current week']):
        week_start = today - timedelta(days=today.weekday())
        date_info = {'type': 'week', 'start_date': week_start, 'end_date': today, 'display': f'This Week ({week_start.strftime("%d %b")} - {today.strftime("%d %b %Y")})'}
    
    # ===== LAST WEEK =====
    elif any(word in question_lower for word in ['last week', 'pichle hafte', 'پچھلے ہفتے', 'previous week']):
        week_start = today - timedelta(days=today.weekday() + 7)
        week_end = week_start + timedelta(days=6)
        date_info = {'type': 'week', 'start_date': week_start, 'end_date': week_end, 'display': f'Last Week ({week_start.strftime("%d %b")} - {week_end.strftime("%d %b %Y")})'}
    
    # ===== THIS MONTH =====
    elif any(word in question_lower for word in ['this month', 'is mahine', 'اس مہینے', 'current month']):
        month_start = today.replace(day=1)
        date_info = {'type': 'month', 'start_date': month_start, 'end_date': today, 'display': f'This Month ({today.strftime("%B %Y")})'}
    
    # ===== LAST MONTH =====
    elif any(word in question_lower for word in ['last month', 'pichle mahine', 'پچھلے مہینے', 'previous month']):
        first_day_current = today.replace(day=1)
        last_day_prev = first_day_current - timedelta(days=1)
        first_day_prev = last_day_prev.replace(day=1)
        date_info = {'type': 'month', 'start_date': first_day_prev, 'end_date': last_day_prev, 'display': f'Last Month ({last_day_prev.strftime("%B %Y")})'}
    
    # ===== THIS YEAR =====
    elif any(word in question_lower for word in ['this year', 'is saal', 'اس سال', 'current year']):
        year_start = today.replace(month=1, day=1)
        date_info = {'type': 'year', 'start_date': year_start, 'end_date': today, 'display': f'This Year ({today.year})'}
    
    # ===== LAST YEAR =====
    elif any(word in question_lower for word in ['last year', 'pichle saal', 'پچھلے سال', 'previous year']):
        year_start = today.replace(month=1, day=1) - timedelta(days=365)
        year_end = today.replace(month=1, day=1) - timedelta(days=1)
        date_info = {'type': 'year', 'start_date': year_start, 'end_date': year_end, 'display': f'Last Year ({year_start.year})'}
    
    # ===== SPECIFIC MONTH (e.g., "july 2026") =====
    else:
        import re
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        urdu_months = {
            'جنوری': 'january', 'فروری': 'february', 'مارچ': 'march',
            'اپریل': 'april', 'مئی': 'may', 'جون': 'june',
            'جولائی': 'july', 'اگست': 'august', 'ستمبر': 'september',
            'اکتوبر': 'october', 'نومبر': 'november', 'دسمبر': 'december'
        }
        
        # Pattern: month_name year
        month_pattern = r'(january|february|march|april|may|june|july|august|september|october|november|december|جنوری|فروری|مارچ|اپریل|مئی|جون|جولائی|اگست|ستمبر|اکتوبر|نومبر|دسمبر)\s*(\d{4})?'
        month_match = re.search(month_pattern, question_lower)
        
        if month_match:
            month_name = month_match.group(1)
            year = int(month_match.group(2)) if month_match.group(2) else today.year
            
            month_name = urdu_months.get(month_name, month_name)
            month_num = months.get(month_name, today.month)
            
            month_start = datetime(year, month_num, 1).date()
            if month_num == 12:
                month_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                month_end = datetime(year, month_num + 1, 1).date() - timedelta(days=1)
            
            date_info = {
                'type': 'month',
                'start_date': month_start,
                'end_date': month_end,
                'display': f'{month_name.capitalize()} {year}'
            }
        
        # ===== SPECIFIC DATE (e.g., "10 july 2026") =====
        else:
            date_pattern = r'(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|جنوری|فروری|مارچ|اپریل|مئی|جون|جولائی|اگست|ستمبر|اکتوبر|نومبر|دسمبر)\s*(\d{4})?'
            date_match = re.search(date_pattern, question_lower)
            
            if date_match:
                day = int(date_match.group(1))
                month_name = date_match.group(2)
                year = int(date_match.group(3)) if date_match.group(3) else today.year
                
                month_name = urdu_months.get(month_name, month_name)
                month_num = months.get(month_name, today.month)
                
                try:
                    specific_date = datetime(year, month_num, day).date()
                    if specific_date <= today:
                        date_info = {
                            'type': 'specific',
                            'start_date': specific_date,
                            'end_date': specific_date,
                            'display': specific_date.strftime('%d %B %Y')
                        }
                except:
                    pass
    
    return date_info


def get_shop_data_for_date_range(date_info):
    """Get all shop data for date range"""
    start_date = date_info['start_date']
    end_date = date_info['end_date']
    
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # ===== SALES =====
    sales = Sale.query.filter(Sale.created_at.between(start_datetime, end_datetime)).all()
    total_sales = sum(s.total_amount for s in sales)
    sales_count = len(sales)
    
    # ===== PHOTOCOPY =====
    photocopy = PhotocopyJob.query.filter(PhotocopyJob.created_at.between(start_datetime, end_datetime)).all()
    total_photocopy = sum(j.total_amount for j in photocopy)
    photocopy_count = len(photocopy)
    
    # ===== WALLET =====
    wallet = MobileWalletTransaction.query.filter(
        MobileWalletTransaction.created_at.between(start_datetime, end_datetime)
    ).all()
    wallet_receive = sum(w.amount for w in wallet if w.transaction_type == 'receive')
    wallet_send = sum(w.amount for w in wallet if w.transaction_type == 'send')
    wallet_profit = (wallet_send * 0.01) + (wallet_receive * 0.02)
    wallet_count = len(wallet)
    
    # ===== DATA REVENUE =====
    data_revenue = DataRevenue.query.filter(
        DataRevenue.created_at.between(start_datetime, end_datetime)
    ).all()
    total_data = sum(d.amount for d in data_revenue)
    data_count = len(data_revenue)
    
    # ===== BILL PAYMENTS =====
    bills = BillPayment.query.filter(
        BillPayment.created_at.between(start_datetime, end_datetime)
    ).all()
    bill_profit = sum(b.profit_amount for b in bills)
    bill_count = len(bills)
    
    # ===== EXPENSES =====
    expenses = Expense.query.filter(Expense.expense_date.between(start_datetime, end_datetime)).all()
    total_expenses = sum(e.amount for e in expenses)
    expense_count = len(expenses)
    
    # ===== TOTALS =====
    total_revenue = total_sales + total_photocopy + wallet_profit + total_data + bill_profit
    net_profit = total_revenue - total_expenses
    
    # ===== CUSTOMERS =====
    new_customers = Customer.query.filter(
        Customer.created_at.between(start_datetime, end_datetime)
    ).count()
    total_customers = Customer.query.count()
    
    # ===== DUES =====
    total_due = db.session.query(func.sum(Customer.total_due)).scalar() or 0
    
    # ===== PRODUCTS =====
    total_products = Product.query.filter_by(is_active=True).count()
    low_stock = Product.query.filter(
        Product.stock_quantity <= Product.min_stock_level,
        Product.is_active == True
    ).count()
    out_of_stock = Product.query.filter(
        Product.stock_quantity == 0,
        Product.is_active == True
    ).count()
    
    # ===== TOP PRODUCTS =====
    top_products = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_sold'),
        func.sum(SaleItem.total_price).label('total_revenue')
    ).join(SaleItem).join(Sale).filter(
        Sale.created_at.between(start_datetime, end_datetime)
    ).group_by(Product.id).order_by(func.sum(SaleItem.quantity).desc()).limit(5).all()
    
    # ===== TOP CUSTOMERS =====
    top_customers = db.session.query(
        Customer.name,
        func.sum(Sale.total_amount).label('total_spent')
    ).join(Sale).filter(
        Sale.created_at.between(start_datetime, end_datetime)
    ).group_by(Customer.id).order_by(func.sum(Sale.total_amount).desc()).limit(5).all()
    
    # ===== PAYMENT METHODS =====
    payment_methods = db.session.query(
        Sale.payment_method,
        func.count(Sale.id).label('count'),
        func.sum(Sale.total_amount).label('total')
    ).filter(
        Sale.created_at.between(start_datetime, end_datetime)
    ).group_by(Sale.payment_method).all()
    
    days_in_range = (end_date - start_date).days + 1
    avg_daily_sales = total_sales / days_in_range if days_in_range > 0 else 0
    avg_daily_profit = net_profit / days_in_range if days_in_range > 0 else 0
    
    return {
        'date_info': date_info,
        'days_in_range': days_in_range,
        'total_sales': total_sales,
        'sales_count': sales_count,
        'total_photocopy': total_photocopy,
        'photocopy_count': photocopy_count,
        'wallet_receive': wallet_receive,
        'wallet_send': wallet_send,
        'wallet_profit': wallet_profit,
        'wallet_count': wallet_count,
        'total_data': total_data,
        'data_count': data_count,
        'bill_profit': bill_profit,
        'bill_count': bill_count,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'expense_count': expense_count,
        'net_profit': net_profit,
        'new_customers': new_customers,
        'total_customers': total_customers,
        'total_due': total_due,
        'total_products': total_products,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'top_products': top_products,
        'top_customers': top_customers,
        'payment_methods': payment_methods,
        'avg_daily_sales': avg_daily_sales,
        'avg_daily_profit': avg_daily_profit,
        'start_date': start_date,
        'end_date': end_date
    }


def generate_intelligent_response(question, data, date_info):
    """Generate intelligent response based on ANY question"""
    
    question_lower = question.lower()
    display_date = date_info['display']
    
    # ===== CHECK WHAT USER IS ASKING =====
    
    # 1. GREETINGS
    if any(word in question_lower for word in ['hi', 'hello', 'hey', 'salam', 'assalam', 'good morning', 'good evening', 'good afternoon', 'how are you', 'kia hal', 'کیا حال']):
        return f"""Assalam o Alaikum Abdul Hanan! 👋

I'm your shop assistant. Here's what I can help you with:

📊 **Quick Stats ({display_date}):**
- Revenue: PKR {data['total_revenue']:,.0f}
- Profit: PKR {data['net_profit']:,.0f}
- Sales: {data['sales_count']} orders

💬 **You can ask me ANYTHING about your shop:**
- "Today kitni sale hui?"
- "Aj ka profit kya hai?"
- "Photocopy ka hisab batao"
- "10 july 2026 ki sale"
- "This month ka revenue"
- "Low stock items"
- "Top customers"
- "Expenses"

Just type naturally, I'll understand! 😊"""

    # 2. PHOTOCOPY (ANY VARIATION)
    if any(word in question_lower for word in ['photocopy', 'photo copy', 'فوٹو کاپی', 'copy', 'prints', 'پرنٹس', 'photo state']):
        return f"""🖨️ **Photocopy Report - {display_date}**

📊 Total Jobs: {data['photocopy_count']}
💰 Total Revenue: PKR {data['total_photocopy']:,.0f}
📄 Average per Job: PKR {(data['total_photocopy'] / data['photocopy_count']) if data['photocopy_count'] > 0 else 0:,.0f}

📈 **Performance:**
{'🌟 Excellent photocopy business today!' if data['photocopy_count'] > 10 else '📈 Good number of jobs!' if data['photocopy_count'] > 5 else '📊 Keep promoting photocopy services!'}

💡 **Tip:** {'Consider offering bulk discounts to increase jobs!' if data['photocopy_count'] < 10 else 'You\'re doing great with photocopy!'}"""

    # 3. WALLET / MOBILE WALLET
    if any(word in question_lower for word in ['wallet', 'mobile wallet', 'jazzcash', 'easypaisa', 'والیٹ', 'موبائل والیٹ']):
        return f"""📱 **Mobile Wallet Report - {display_date}**

💰 Total Transactions: {data['wallet_count']}
📥 Received: PKR {data['wallet_receive']:,.0f}
📤 Sent: PKR {data['wallet_send']:,.0f}
✅ **Profit:** PKR {data['wallet_profit']:,.0f}

📈 **Breakdown:**
• Receive Profit (2%): PKR {data['wallet_receive'] * 0.02:,.0f}
• Send Profit (1%): PKR {data['wallet_send'] * 0.01:,.0f}

{'🌟 Great wallet business today!' if data['wallet_count'] > 5 else '📈 Keep promoting wallet services!'}"""

    # 4. DATA REVENUE
    if any(word in question_lower for word in ['data revenue', 'data', 'movies', 'songs', 'cartoon', 'ڈیٹا', 'موویز', 'گانے']):
        return f"""🎬 **Data Revenue Report - {display_date}**

💰 Total Revenue: PKR {data['total_data']:,.0f}
📦 Total Entries: {data['data_count']}

📊 **Categories:**
• Movies 🎬
• Songs 🎵
• Cartoon 🎨
• Vlogs 📹
• Other 📦

{'🌟 Strong data revenue today!' if data['total_data'] > 1000 else '📈 Keep adding data content!'}"""

    # 5. BILL PAYMENT
    if any(word in question_lower for word in ['bill', 'bills', 'bill payment', 'بل', 'بل ادائیگی']):
        return f"""📄 **Bill Payment Report - {display_date}**

💰 Total Profit: PKR {data['bill_profit']:,.0f}
📦 Total Bills: {data['bill_count']}

📊 **Rule:**
• Bill < PKR 5,000 → Profit PKR 20
• Bill ≥ PKR 5,000 → Profit PKR 50

{'🌟 Good bill payment business!' if data['bill_count'] > 3 else '📈 Promote bill payment services!'}"""

    # 6. EXPENSES
    if any(word in question_lower for word in ['expense', 'expenses', 'خرچ', 'اخراجات', 'cost']):
        return f"""💸 **Expenses Report - {display_date}**

💰 Total Expenses: PKR {data['total_expenses']:,.0f}
📋 Total Entries: {data['expense_count']}
📊 Revenue: PKR {data['total_revenue']:,.0f}

📈 **Expense Ratio:** {((data['total_expenses'] / data['total_revenue']) * 100) if data['total_revenue'] > 0 else 0:.1f}%

{'🟢 Excellent expense management!' if (data['total_expenses'] / data['total_revenue']) < 0.3 else '🟡 Review your expenses' if (data['total_expenses'] / data['total_revenue']) < 0.5 else '🔴 High expenses! Check where you can save'}"""

    # 7. STOCK
    if any(word in question_lower for word in ['stock', 'inventory', 'اسٹاک', 'انوینٹری', 'products', 'products']):
        return f"""📦 **Inventory Report - {display_date}**

📦 Total Products: {data['total_products']}
⚠️ Low Stock: {data['low_stock']}
🚫 Out of Stock: {data['out_of_stock']}
✅ In Stock: {data['total_products'] - data['low_stock'] - data['out_of_stock']}

📊 **Status:**
{'🟢 Healthy inventory!' if data['low_stock'] == 0 and data['out_of_stock'] == 0 else '🟡 Some items need attention!' if data['low_stock'] > 0 else '🔴 Out of stock items! Reorder immediately!'}

💡 **Action Required:** {'Check products page and reorder items' if data['low_stock'] > 0 or data['out_of_stock'] > 0 else 'Keep up the good inventory management!'}"""

    # 8. CUSTOMERS
    if any(word in question_lower for word in ['customer', 'customers', 'کسٹمر', 'کسٹمرز', 'buyer']):
        return f"""👥 **Customers Report - {display_date}**

👤 Total Customers: {data['total_customers']}
🆕 New Customers: {data['new_customers']}
💰 Total Due: PKR {data['total_due']:,.0f}

📊 **Top Customers:**
{chr(10).join([f"• {c.name}: PKR {c.total_spent:,.0f}" for c in data['top_customers'][:5]]) if data['top_customers'] else '• No customer data available'}

💡 **Tip:** {'Follow up with customers who have due payments!' if data['total_due'] > 0 else 'Great! No outstanding dues!'}"""

    # 9. REVENUE / SALES
    if any(word in question_lower for word in ['revenue', 'sales', 'sale', 'sell', 'sell', 'ریونیو', 'سیل', 'sell']):
        return f"""📊 **Sales Report - {display_date}**

💰 Total Revenue: PKR {data['total_revenue']:,.0f}
📦 Total Orders: {data['sales_count']}
📈 Average per Order: PKR {(data['total_sales'] / data['sales_count']) if data['sales_count'] > 0 else 0:,.0f}

📋 **Breakdown:**
• Product Sales: PKR {data['total_sales']:,.0f}
• Photocopy: PKR {data['total_photocopy']:,.0f}
• Wallet Profit: PKR {data['wallet_profit']:,.0f}
• Data Revenue: PKR {data['total_data']:,.0f}
• Bill Profit: PKR {data['bill_profit']:,.0f}

✅ **Net Profit:** PKR {data['net_profit']:,.0f}

{'🌟 Excellent sales performance!' if data['total_revenue'] > 50000 else '📈 Good sales!' if data['total_revenue'] > 10000 else '📊 Keep pushing for more sales!'}"""

    # 10. PROFIT
    if any(word in question_lower for word in ['profit', 'منافع', 'earning', 'income']):
        return f"""💰 **Profit Report - {display_date}**

✅ **Net Profit:** PKR {data['net_profit']:,.0f}
📊 Total Revenue: PKR {data['total_revenue']:,.0f}
💸 Total Expenses: PKR {data['total_expenses']:,.0f}

📈 **Profit Margin:** {((data['net_profit'] / data['total_revenue']) * 100) if data['total_revenue'] > 0 else 0:.1f}%

📋 **Profit Breakdown:**
• Sales: PKR {data['total_sales']:,.0f}
• Photocopy: PKR {data['total_photocopy']:,.0f}
• Wallet: PKR {data['wallet_profit']:,.0f}
• Data: PKR {data['total_data']:,.0f}
• Bills: PKR {data['bill_profit']:,.0f}

{'🌟 Excellent profit margin!' if data['net_profit'] > 10000 else '📈 Good profit!' if data['net_profit'] > 0 else '🔴 Loss! Review expenses and increase sales!'}"""

    # 11. COMPARE TODAY VS YESTERDAY
    if 'compare' in question_lower and ('today' in question_lower or 'yesterday' in question_lower):
        # Get yesterday data
        yesterday = datetime.now().date() - timedelta(days=1)
        yesterday_info = {'type': 'yesterday', 'start_date': yesterday, 'end_date': yesterday, 'display': 'Yesterday'}
        yesterday_data = get_shop_data_for_date_range(yesterday_info)
        
        diff_revenue = data['total_revenue'] - yesterday_data['total_revenue']
        diff_profit = data['net_profit'] - yesterday_data['net_profit']
        diff_sales = data['sales_count'] - yesterday_data['sales_count']
        
        return f"""📊 **Comparison: Today vs Yesterday**

📅 **Today:** {data['total_revenue']:,.0f} revenue | {data['net_profit']:,.0f} profit | {data['sales_count']} orders
📅 **Yesterday:** {yesterday_data['total_revenue']:,.0f} revenue | {yesterday_data['net_profit']:,.0f} profit | {yesterday_data['sales_count']} orders

📈 **Difference:**
• Revenue: {'+' if diff_revenue > 0 else ''}{diff_revenue:,.0f} ({'↑' if diff_revenue > 0 else '↓'})
• Profit: {'+' if diff_profit > 0 else ''}{diff_profit:,.0f} ({'↑' if diff_profit > 0 else '↓'})
• Orders: {'+' if diff_sales > 0 else ''}{diff_sales} ({'↑' if diff_sales > 0 else '↓'})

{'🌟 Today is better than yesterday!' if diff_revenue > 0 else '📈 Keep pushing to improve!'}"""

    # 12. SUMMARY (ANYTHING ELSE - FULL OVERVIEW)
    return f"""📊 **Complete Shop Summary - {display_date}**

💰 **Revenue & Profit:**
• Total Revenue: PKR {data['total_revenue']:,.0f}
• Net Profit: PKR {data['net_profit']:,.0f}
• Expenses: PKR {data['total_expenses']:,.0f}

📦 **Sales:**
• Orders: {data['sales_count']}
• Avg per Order: PKR {(data['total_sales'] / data['sales_count']) if data['sales_count'] > 0 else 0:,.0f}

🖨️ **Photocopy:**
• Jobs: {data['photocopy_count']}
• Revenue: PKR {data['total_photocopy']:,.0f}

📱 **Wallet:**
• Transactions: {data['wallet_count']}
• Profit: PKR {data['wallet_profit']:,.0f}

📄 **Bills:**
• Payments: {data['bill_count']}
• Profit: PKR {data['bill_profit']:,.0f}

👥 **Customers:**
• New: {data['new_customers']}
• Total: {data['total_customers']}
• Due: PKR {data['total_due']:,.0f}

📦 **Inventory:**
• Total Products: {data['total_products']}
• Low Stock: {data['low_stock']}
• Out of Stock: {data['out_of_stock']}

📈 **Overall Status:** {'🟢 Excellent business performance!' if data['net_profit'] > 10000 else '🟡 Good performance, keep improving!' if data['net_profit'] > 0 else '🔴 Focus on increasing revenue and reducing expenses!'}

💡 **Recommendation:** {'Give discounts to top customers' if data['top_customers'] else 'Focus on building customer base'}"""
# ==================== INITIALIZE DATABASE ====================

if __name__ == '__main__':
    with app.app_context():
        try:
            from sqlalchemy import inspect, text
            
            # Check if theme_preference column exists
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'theme_preference' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE users ADD COLUMN theme_preference TEXT DEFAULT \'auto\''))
                    conn.commit()
                print("✅ Theme preference column added to users table!")
            else:
                print("✅ Theme preference column already exists!")
            
            # 🆕 Check if bill_payments table exists
            if 'bill_payments' not in inspector.get_table_names():
                print("⚠️ Bill payments table not found! Please run setup_db.py")
            else:
                print("✅ Bill payments table exists!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            print("⚠️ Please run: python setup_db.py")
            exit(1)
        
        print("🚀 Application initialized successfully!")
        print("📊 Database URL:", app.config['SQLALCHEMY_DATABASE_URI'])
        print("🌐 Server running at: http://127.0.0.1:5000")
    
    app.run(debug=False, host='0.0.0.0', port=5000)
