"""
RideNow - Authentication Routes
Handles login, registration, logout for Users, Drivers, and Admins
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from models.models import db, User, Driver, Admin
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


# ── Home / Landing page ────────────────────────────────────────────────────────
@auth_bp.route('/')
def index():
    return render_template('pages/landing.html')


# ── User Registration ──────────────────────────────────────────────────────────
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        # Validation
        if not all([name, email, phone, password, confirm]):
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html')
        if User.query.filter_by(phone=phone).first():
            flash('Phone number already registered.', 'danger')
            return render_template('auth/register.html')

        user = User(name=name, email=email, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


# ── User Login ─────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if user.is_blocked:
                flash('Your account has been blocked. Contact support.', 'danger')
                return render_template('auth/login.html')
            login_user(user, remember=remember)
            session['role'] = 'user'
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(next_page or url_for('user.dashboard'))

        flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html')


# ── Driver Registration ────────────────────────────────────────────────────────
@auth_bp.route('/driver/register', methods=['GET', 'POST'])
def driver_register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        license_number = request.form.get('license_number', '').strip().upper()
        vehicle_number = request.form.get('vehicle_number', '').strip().upper()
        vehicle_type = request.form.get('vehicle_type', '')
        vehicle_model = request.form.get('vehicle_model', '').strip()
        vehicle_color = request.form.get('vehicle_color', '').strip()

        if not all([name, email, phone, password, confirm, license_number,
                    vehicle_number, vehicle_type, vehicle_model, vehicle_color]):
            flash('All fields are required.', 'danger')
            return render_template('auth/driver_register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/driver_register.html')
        if Driver.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/driver_register.html')
        if Driver.query.filter_by(license_number=license_number).first():
            flash('License number already registered.', 'danger')
            return render_template('auth/driver_register.html')
        if Driver.query.filter_by(vehicle_number=vehicle_number).first():
            flash('Vehicle number already registered.', 'danger')
            return render_template('auth/driver_register.html')

        driver = Driver(
            name=name, email=email, phone=phone,
            license_number=license_number, vehicle_number=vehicle_number,
            vehicle_type=vehicle_type, vehicle_model=vehicle_model,
            vehicle_color=vehicle_color
        )
        driver.set_password(password)
        db.session.add(driver)
        db.session.commit()
        flash('Driver registration submitted! Await admin verification.', 'success')
        return redirect(url_for('auth.driver_login'))

    return render_template('auth/driver_register.html')


# ── Driver Login ───────────────────────────────────────────────────────────────
@auth_bp.route('/driver/login', methods=['GET', 'POST'])
def driver_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        driver = Driver.query.filter_by(email=email).first()
        if driver and driver.check_password(password):
            if driver.is_blocked:
                flash('Your account has been blocked. Contact support.', 'danger')
                return render_template('auth/driver_login.html')
            if not driver.is_verified:
                flash('Your account is pending verification by admin.', 'warning')
                return render_template('auth/driver_login.html')
            login_user(driver)
            session['role'] = 'driver'
            flash(f'Welcome, {driver.name}!', 'success')
            return redirect(url_for('driver.dashboard'))

        flash('Invalid email or password.', 'danger')

    return render_template('auth/driver_login.html')


# ── Admin Login ────────────────────────────────────────────────────────────────
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        admin = Admin.query.filter_by(email=email).first()
        if admin and admin.check_password(password):
            login_user(admin)
            session['role'] = 'admin'
            flash('Admin login successful.', 'success')
            return redirect(url_for('admin.dashboard'))

        flash('Invalid admin credentials.', 'danger')

    return render_template('auth/admin_login.html')


# ── Forgot Password ────────────────────────────────────────────────────────────
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Password reset instructions sent to your email. (Demo: use password User@123)', 'info')
        else:
            flash('If this email exists, reset instructions will be sent.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html')


# ── Logout ─────────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
@login_required
def logout():
    role = session.get('role', 'user')
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    if role == 'driver':
        return redirect(url_for('auth.driver_login'))
    elif role == 'admin':
        return redirect(url_for('auth.admin_login'))
    return redirect(url_for('auth.login'))