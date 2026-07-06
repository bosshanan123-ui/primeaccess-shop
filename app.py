# app.py - Complete Main Application with Theme System

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

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, make_response
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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
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

# ---------- Dashboard Routes ----------

@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    today_sales = Sale.query.filter(Sale.created_at.between(today_start, today_end)).all()
    total_sales_today = sum(sale.total_amount for sale in today_sales)
    total_sales_count = len(today_sales)
    
    today_photocopy = PhotocopyJob.query.filter(PhotocopyJob.created_at.between(today_start, today_end)).all()
    total_prints_today = sum(job.total_pages for job in today_photocopy)
    total_photocopy_revenue = sum(job.total_amount for job in today_photocopy)
    
    today_expenses = Expense.query.filter(Expense.expense_date.between(today_start, today_end)).all()
    total_expenses_today = sum(expense.amount for expense in today_expenses)
    
    today_dues = CustomerDue.query.filter(CustomerDue.due_date.between(today_start, today_end), 
                                         CustomerDue.status == 'pending').all()
    due_amount_today = sum(due.remaining_amount or due.amount for due in today_dues)
    
    low_stock = Product.query.filter(Product.stock_quantity <= Product.min_stock_level).all()
    out_of_stock = Product.query.filter(Product.stock_quantity == 0).all()
    
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_sales = Sale.query.filter(Sale.created_at >= month_start).all()
    total_monthly_sales = sum(sale.total_amount for sale in monthly_sales)
    
    week_start = datetime.now() - timedelta(days=7)
    weekly_sales = Sale.query.filter(Sale.created_at >= week_start).all()
    total_weekly_sales = sum(sale.total_amount for sale in weekly_sales)
    
    recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(10).all()
    recent_photocopy = PhotocopyJob.query.order_by(PhotocopyJob.created_at.desc()).limit(5).all()
    recent_expenses = Expense.query.order_by(Expense.expense_date.desc()).limit(5).all()
    
    total_customers = Customer.query.count()
    new_customers_today = Customer.query.filter(Customer.created_at.between(today_start, today_end)).count()
    
    total_products = Product.query.filter_by(is_active=True).count()
    total_products_value = db.session.query(func.sum(Product.purchase_price * Product.stock_quantity)).scalar() or 0
    
    days = [(datetime.now() - timedelta(days=i)).date() for i in range(7, -1, -1)]
    daily_sales_data = []
    for day in days:
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        day_sales = Sale.query.filter(Sale.created_at.between(day_start, day_end)).all()
        daily_sales_data.append(sum(sale.total_amount for sale in day_sales))
    
    top_products = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_sold')
    ).join(SaleItem).group_by(Product.id).order_by(func.sum(SaleItem.quantity).desc()).limit(10).all()
    
    payment_methods = db.session.query(
        Sale.payment_method,
        func.count(Sale.id).label('count'),
        func.sum(Sale.total_amount).label('total')
    ).group_by(Sale.payment_method).all()
    
    context = {
        'total_sales_today': total_sales_today,
        'total_sales_count': total_sales_count,
        'total_prints_today': total_prints_today,
        'total_photocopy_revenue': total_photocopy_revenue,
        'total_expenses_today': total_expenses_today,
        'due_amount_today': due_amount_today,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'low_stock_count': len(low_stock),
        'out_of_stock_count': len(out_of_stock),
        'total_monthly_sales': total_monthly_sales,
        'total_weekly_sales': total_weekly_sales,
        'recent_sales': recent_sales,
        'recent_photocopy': recent_photocopy,
        'recent_expenses': recent_expenses,
        'total_customers': total_customers,
        'new_customers_today': new_customers_today,
        'total_products': total_products,
        'total_products_value': total_products_value,
        'daily_sales_data': daily_sales_data,
        'days': days,
        'top_products': top_products,
        'payment_methods': payment_methods,
        'net_profit_today': total_sales_today + total_photocopy_revenue - total_expenses_today
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
        
        # ✅ Sale Items - Correct indentation (8 spaces from start of function)
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
        
        # ✅ Customer Due - Correct indentation (8 spaces)
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
        
        # ✅ Customer update - Correct indentation (8 spaces)
        if customer_id:
            customer = Customer.query.get(int(customer_id))
            if customer:
                customer.total_purchases += total_amount
                customer.total_visits += 1
                customer.last_purchase = datetime.utcnow()
        
        # ✅ Audit Log - Correct indentation (8 spaces)
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

@app.route('/reports/sales')
@login_required
def reports_sales():
    try:
        # PostgreSQL compatible monthly grouping
        # Use EXTRACT or to_char for PostgreSQL
        monthly_data = db.session.query(
            func.to_char(Sale.created_at, 'YYYY-MM').label('month'),
            func.sum(Sale.total_amount).label('total_sales'),
            func.count(Sale.id).label('total_orders')
        ).group_by(
            func.to_char(Sale.created_at, 'YYYY-MM')
        ).order_by(
            func.to_char(Sale.created_at, 'YYYY-MM')
        ).all()
        
        # Convert to list of dicts
        sales_data = []
        total_sales = 0
        total_orders = 0
        
        for data in monthly_data:
            sales_data.append({
                'month': data.month,
                'total_sales': float(data.total_sales or 0),
                'total_orders': data.total_orders or 0
            })
            total_sales += float(data.total_sales or 0)
            total_orders += data.total_orders or 0
        
        avg_order_value = total_sales / total_orders if total_orders > 0 else 0
        
        return render_template('reports_sales.html', 
                             sales_data=sales_data,
                             total_sales=total_sales,
                             total_orders=total_orders,
                             avg_order_value=avg_order_value)
    except Exception as e:
        print(f"Sales Report Error: {str(e)}")
        # Fallback: Get total sales without grouping
        try:
            total_sales = db.session.query(func.sum(Sale.total_amount)).scalar() or 0
            total_orders = db.session.query(func.count(Sale.id)).scalar() or 0
            avg_order_value = total_sales / total_orders if total_orders > 0 else 0
            
            # Try to get monthly data with alternative method
            monthly_data = []
            # Get last 6 months
            for i in range(6, 0, -1):
                month_date = datetime.now() - timedelta(days=30*i)
                month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                month_end = (month_start + timedelta(days=32)).replace(day=1)
                
                month_sales = Sale.query.filter(
                    Sale.created_at >= month_start,
                    Sale.created_at < month_end
                ).all()
                
                monthly_data.append({
                    'month': month_start.strftime('%Y-%m'),
                    'total_sales': sum(s.total_amount for s in month_sales),
                    'total_orders': len(month_sales)
                })
            
            return render_template('reports_sales.html', 
                                 sales_data=monthly_data,
                                 total_sales=total_sales,
                                 total_orders=total_orders,
                                 avg_order_value=avg_order_value)
        except Exception as e2:
            print(f"Sales Report Fallback Error: {str(e2)}")
            return render_template('reports_sales.html', 
                                 sales_data=[], 
                                 total_sales=0, 
                                 total_orders=0, 
                                 avg_order_value=0)

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
# ---------- Backup Routes ----------

@app.route('/backup', methods=['GET', 'POST'])
@login_required
def backup():
    if request.method == 'POST':
        try:
            # Create backups directory if it doesn't exist
            backup_dir = 'backups'
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                print(f"✅ Created backups directory: {backup_dir}")
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"backup_{timestamp}.json"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # For Supabase PostgreSQL - Export data as JSON
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            backup_data = {}
            for table in tables:
                if table.startswith('sqlite_'):
                    continue
                try:
                    # Query all data from the table
                    result = db.session.execute(f'SELECT * FROM {table}').fetchall()
                    # Convert to list of dicts
                    backup_data[table] = [dict(row._mapping) for row in result]
                except Exception as e:
                    print(f"Error backing up table {table}: {str(e)}")
                    backup_data[table] = []
            
            # Write to JSON file
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, default=str, indent=2)
            
            # Save backup record in database
            backup = Backup(
                filename=backup_filename,
                size=os.path.getsize(backup_path),
                type='manual',
                created_by=current_user.id,
                notes=f'Manual backup by {current_user.username}'
            )
            db.session.add(backup)
            db.session.commit()
            
            flash('✅ Backup created successfully!', 'success')
            
        except Exception as e:
            print(f"Backup Error: {str(e)}")
            flash(f'❌ Error creating backup: {str(e)}', 'danger')
        
        return redirect(url_for('backup'))
    
    backups = Backup.query.order_by(Backup.backup_date.desc()).all()
    return render_template('backup.html', backups=backups)

@app.route('/backup/download/<int:backup_id>')
@login_required
def download_backup(backup_id):
    backup = Backup.query.get_or_404(backup_id)
    backup_path = os.path.join('backups', backup.filename)
    
    if os.path.exists(backup_path):
        return send_file(
            backup_path, 
            as_attachment=True, 
            download_name=backup.filename
        )
    else:
        flash('❌ Backup file not found.', 'danger')
        return redirect(url_for('backup'))

@app.route('/backup/export_excel/<int:backup_id>')
@login_required
def export_backup_excel(backup_id):
    backup = Backup.query.get_or_404(backup_id)
    backup_path = os.path.join('backups', backup.filename)
    
    if not os.path.exists(backup_path):
        flash('❌ Backup file not found!', 'danger')
        return redirect(url_for('backup'))
    
    try:
        # Load JSON data
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for table_name, data in backup_data.items():
                if data:
                    df = pd.DataFrame(data)
                    sheet_name = table_name[:31]  # Excel sheet name max 31 chars
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
                else:
                    # Empty table
                    pd.DataFrame({'Message': ['No data found']}).to_excel(
                        writer, sheet_name=table_name[:31], index=False
                    )
        
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"backup_{backup.backup_date.strftime('%Y%m%d_%H%M')}.xlsx"
        )
        
    except Exception as e:
        print(f"Export Error: {str(e)}")
        flash(f'❌ Error exporting backup: {str(e)}', 'danger')
        return redirect(url_for('backup'))

# ============ API ROUTES FOR BACKUP ============

@app.route('/api/backup/filter', methods=['POST'])
@login_required
def filter_backups():
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
    try:
        backup = Backup.query.get_or_404(backup_id)
        
        # Delete file from filesystem
        file_path = os.path.join('backups', backup.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✅ Deleted backup file: {file_path}")
        
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

# ---------- Theme Preference Routes ----------

@app.route('/api/theme/preference', methods=['POST'])
@login_required
def save_theme_preference():
    """Save user's theme preference to database"""
    data = request.json
    theme_mode = data.get('theme_mode', 'auto')
    
    valid_modes = ['light', 'dark', 'auto', 'light-sensor']
    if theme_mode not in valid_modes:
        return jsonify({
            'status': 'error',
            'message': 'Invalid theme mode'
        }), 400
    
    current_user.theme_preference = theme_mode
    db.session.commit()
    session['theme_mode'] = theme_mode
    
    return jsonify({
        'status': 'success',
        'theme_mode': theme_mode,
        'message': 'Theme preference saved successfully'
    })
# ============================================
# COLOR THEME ROUTES - ADD THESE NEW ROUTES
# ============================================

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
        session['theme'] = mode  # Keep backward compatibility
        # Also save to database
        current_user.theme_preference = mode
        db.session.commit()
        return jsonify({'status': 'success', 'mode': mode})
    return jsonify({'status': 'error', 'message': 'Invalid mode'}), 400
@app.route('/api/theme/preference', methods=['GET'])
@login_required
def get_theme_preference():
    """Get user's theme preference"""
    theme_mode = current_user.theme_preference or 'auto'
    return jsonify({
        'status': 'success',
        'theme_mode': theme_mode
    })

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
    transactions = MobileWalletTransaction.query.order_by(MobileWalletTransaction.created_at.desc()).all()
    
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
    
    customers = Customer.query.filter_by(is_active=True).all()
    
    return render_template('mobile_wallet.html', 
                         transactions=transactions,
                         total_received_jazz=total_received_jazz,
                         total_sent_jazz=total_sent_jazz,
                         balance_jazz=balance_jazz,
                         total_received_easy=total_received_easy,
                         total_sent_easy=total_sent_easy,
                         balance_easy=balance_easy,
                         customers=customers)

@app.route('/mobile_wallet/receipt/<int:transaction_id>')
@login_required
def mobile_wallet_receipt(transaction_id):
    transaction = MobileWalletTransaction.query.get_or_404(transaction_id)
    return render_template('mobile_wallet_receipt.html', transaction=transaction)

@app.route('/mobile_wallet/add', methods=['POST'])
@login_required
def add_mobile_wallet():
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
    
    if transaction_type == 'receive' and customer_id:
        customer = Customer.query.get(int(customer_id))
        if customer:
            customer.total_due -= amount
    
    db.session.commit()
    flash(f'{wallet_type.title()} transaction added successfully!', 'success')
    return redirect(url_for('mobile_wallet'))

@app.route('/mobile_wallet/delete/<int:transaction_id>', methods=['POST'])
@login_required
def delete_mobile_wallet(transaction_id):
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

# ==================== INITIALIZE DATABASE ====================

if __name__ == '__main__':
    with app.app_context():
        try:
            import sqlite3
            import os
            if os.path.exists('shop_management.db'):
                conn = sqlite3.connect('shop_management.db')
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(users)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'theme_preference' not in columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN theme_preference TEXT DEFAULT 'auto'")
                    conn.commit()
                    print("✅ Theme preference column added to users table!")
                else:
                    print("✅ Theme preference column already exists!")
                conn.close()
            else:
                print("⚠️ Database not found! Please run: python setup_db.py")
                exit(1)
        except Exception as e:
            print(f"❌ Error: {e}")
            print("⚠️ Please run: python setup_db.py")
            exit(1)
        
        print("🚀 Application initialized successfully!")
        print("📊 Database URL:", app.config['SQLALCHEMY_DATABASE_URI'])
        print("🌐 Server running at: http://127.0.0.1:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
