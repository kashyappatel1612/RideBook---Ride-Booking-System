"""
RideNow - Admin Routes
Full platform management: users, drivers, rides, revenue, analytics
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.models import db, Admin, User, Driver, Ride, Payment, Review, PromoCode
from datetime import datetime, timedelta
from functools import wraps
from sqlalchemy import extract

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not isinstance(current_user._get_current_object(), Admin):
            flash('Admin access only.', 'danger')
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ──────────────────────────────────────────────────────────────────
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_drivers = Driver.query.count()
    total_rides = Ride.query.count()
    total_revenue = db.session.query(db.func.sum(Payment.amount))\
        .filter_by(payment_status='completed').scalar() or 0

    # Today stats
    today = datetime.utcnow().date()
    today_rides = Ride.query.filter(db.func.date(Ride.booked_at) == today).count()
    today_revenue = db.session.query(db.func.sum(Payment.amount))\
        .filter(db.func.date(Payment.paid_at) == today).scalar() or 0

    # Monthly revenue for chart
    monthly_revenue = []
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for m in range(1, 13):
        rev = db.session.query(db.func.sum(Payment.amount))\
            .filter(extract('month', Payment.paid_at) == m,
                    extract('year', Payment.paid_at) == datetime.utcnow().year,
                    Payment.payment_status == 'completed').scalar() or 0
        monthly_revenue.append(round(rev, 2))

    # Vehicle type distribution
    vehicle_stats = db.session.query(
        Ride.vehicle_type, db.func.count(Ride.id)
    ).group_by(Ride.vehicle_type).all()

    # Recent rides
    recent_rides = Ride.query.order_by(Ride.booked_at.desc()).limit(10).all()

    # Pending driver verifications
    pending_drivers = Driver.query.filter_by(is_verified=False, is_blocked=False).count()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_drivers=total_drivers,
                           total_rides=total_rides,
                           total_revenue=round(total_revenue, 2),
                           today_rides=today_rides,
                           today_revenue=round(today_revenue, 2),
                           monthly_revenue=monthly_revenue,
                           months=months,
                           vehicle_stats=vehicle_stats,
                           recent_rides=recent_rides,
                           pending_drivers=pending_drivers)


# ── Manage Users ───────────────────────────────────────────────────────────────
@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    query = User.query
    if search:
        query = query.filter(
            User.name.ilike(f'%{search}%') | User.email.ilike(f'%{search}%')
        )
    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('admin/users.html', users=users, search=search)


@admin_bp.route('/users/toggle-block/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_block_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blocked = not user.is_blocked
    db.session.commit()
    status = 'blocked' if user.is_blocked else 'unblocked'
    flash(f'User {user.name} has been {status}.', 'info')
    return redirect(url_for('admin.manage_users'))


# ── Manage Drivers ─────────────────────────────────────────────────────────────
@admin_bp.route('/drivers')
@login_required
@admin_required
def manage_drivers():
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    query = Driver.query
    if search:
        query = query.filter(
            Driver.name.ilike(f'%{search}%') | Driver.email.ilike(f'%{search}%')
        )
    if status == 'pending':
        query = query.filter_by(is_verified=False, is_blocked=False)
    elif status == 'verified':
        query = query.filter_by(is_verified=True)
    elif status == 'blocked':
        query = query.filter_by(is_blocked=True)
    drivers = query.order_by(Driver.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('admin/drivers.html', drivers=drivers, search=search, status=status)


@admin_bp.route('/drivers/verify/<int:driver_id>', methods=['POST'])
@login_required
@admin_required
def verify_driver(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    driver.is_verified = True
    db.session.commit()
    flash(f'Driver {driver.name} has been verified.', 'success')
    return redirect(url_for('admin.manage_drivers'))


@admin_bp.route('/drivers/toggle-block/<int:driver_id>', methods=['POST'])
@login_required
@admin_required
def toggle_block_driver(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    driver.is_blocked = not driver.is_blocked
    if driver.is_blocked:
        driver.is_available = False
    db.session.commit()
    status = 'blocked' if driver.is_blocked else 'unblocked'
    flash(f'Driver {driver.name} has been {status}.', 'info')
    return redirect(url_for('admin.manage_drivers'))


# ── All Bookings ───────────────────────────────────────────────────────────────
@admin_bp.route('/bookings')
@login_required
@admin_required
def all_bookings():
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    query = Ride.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    rides = query.order_by(Ride.booked_at.desc()).paginate(page=page, per_page=15)
    return render_template('admin/bookings.html', rides=rides,
                           search=search, status_filter=status_filter)


# ── Revenue Reports ────────────────────────────────────────────────────────────
@admin_bp.route('/revenue')
@login_required
@admin_required
def revenue():
    total = db.session.query(db.func.sum(Payment.amount))\
        .filter_by(payment_status='completed').scalar() or 0
    payments = Payment.query.order_by(Payment.paid_at.desc()).limit(50).all()

    # Payment method breakdown
    method_stats = db.session.query(
        Payment.payment_method, db.func.count(Payment.id), db.func.sum(Payment.amount)
    ).filter_by(payment_status='completed').group_by(Payment.payment_method).all()

    return render_template('admin/revenue.html',
                           total_revenue=round(total, 2),
                           payments=payments,
                           method_stats=method_stats)


# ── Promo Codes ────────────────────────────────────────────────────────────────
@admin_bp.route('/promos', methods=['GET', 'POST'])
@login_required
@admin_required
def promos():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        dtype = request.form.get('discount_type')
        dval = float(request.form.get('discount_value', 0))
        maxd = request.form.get('max_discount')
        minf = float(request.form.get('min_fare', 0))
        ulim = request.form.get('usage_limit')
        valid_until = request.form.get('valid_until')

        if PromoCode.query.filter_by(code=code).first():
            flash('Promo code already exists.', 'danger')
        else:
            promo = PromoCode(
                code=code, discount_type=dtype, discount_value=dval,
                max_discount=float(maxd) if maxd else None,
                min_fare=minf,
                usage_limit=int(ulim) if ulim else None,
                valid_until=datetime.strptime(valid_until, '%Y-%m-%d') if valid_until else None,
            )
            db.session.add(promo)
            db.session.commit()
            flash('Promo code created.', 'success')

    promos = PromoCode.query.order_by(PromoCode.created_at.desc()).all()
    return render_template('admin/promos.html', promos=promos)


@admin_bp.route('/promos/toggle/<int:promo_id>', methods=['POST'])
@login_required
@admin_required
def toggle_promo(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    promo.is_active = not promo.is_active
    db.session.commit()
    flash('Promo code status updated.', 'info')
    return redirect(url_for('admin.promos'))