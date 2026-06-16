"""
RideNow - Driver Routes
Dashboard, ride management, earnings for drivers
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models.models import db, Driver, Ride, Review, Payment
from datetime import datetime, timedelta
from functools import wraps

driver_bp = Blueprint('driver', __name__)


def driver_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not isinstance(current_user._get_current_object(), Driver):
            flash('Driver access only.', 'warning')
            return redirect(url_for('auth.driver_login'))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ──────────────────────────────────────────────────────────────────
@driver_bp.route('/dashboard')
@login_required
@driver_required
def dashboard():
    pending_rides = Ride.query.filter_by(status='pending').all()
    my_rides = Ride.query.filter_by(driver_id=current_user.id)\
        .order_by(Ride.booked_at.desc()).limit(10).all()
    active_ride = Ride.query.filter_by(
        driver_id=current_user.id, status='in_progress'
    ).first() or Ride.query.filter_by(
        driver_id=current_user.id, status='accepted'
    ).first()

    today = datetime.utcnow().date()
    today_earnings = db.session.query(db.func.sum(Payment.amount))\
        .join(Ride)\
        .filter(Ride.driver_id == current_user.id,
                db.func.date(Payment.paid_at) == today).scalar() or 0

    week_start = datetime.utcnow() - timedelta(days=7)
    week_earnings = db.session.query(db.func.sum(Payment.amount))\
        .join(Ride)\
        .filter(Ride.driver_id == current_user.id,
                Payment.paid_at >= week_start).scalar() or 0

    completed_today = Ride.query.filter_by(
        driver_id=current_user.id, status='completed'
    ).filter(db.func.date(Ride.completed_at) == today).count()

    return render_template('driver/dashboard.html',
                           pending_rides=pending_rides,
                           my_rides=my_rides,
                           active_ride=active_ride,
                           today_earnings=round(today_earnings, 2),
                           week_earnings=round(week_earnings, 2),
                           completed_today=completed_today)


# ── Accept Ride ────────────────────────────────────────────────────────────────
@driver_bp.route('/accept-ride/<int:ride_id>', methods=['POST'])
@login_required
@driver_required
def accept_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)
    if ride.status != 'pending':
        flash('This ride is no longer available.', 'warning')
        return redirect(url_for('driver.dashboard'))

    ride.status = 'accepted'
    ride.driver_id = current_user.id
    ride.accepted_at = datetime.utcnow()
    current_user.is_available = False
    db.session.commit()
    flash('Ride accepted! Head to pickup location.', 'success')
    return redirect(url_for('driver.ride_detail', ride_id=ride.id))


# ── Reject Ride ────────────────────────────────────────────────────────────────
@driver_bp.route('/reject-ride/<int:ride_id>', methods=['POST'])
@login_required
@driver_required
def reject_ride(ride_id):
    # Driver rejects — just redirect back, don't assign
    flash('Ride rejected.', 'info')
    return redirect(url_for('driver.dashboard'))


# ── Start Ride ─────────────────────────────────────────────────────────────────
@driver_bp.route('/start-ride/<int:ride_id>', methods=['POST'])
@login_required
@driver_required
def start_ride(ride_id):
    ride = Ride.query.filter_by(id=ride_id, driver_id=current_user.id).first_or_404()
    if ride.status == 'accepted':
        ride.status = 'in_progress'
        ride.started_at = datetime.utcnow()
        db.session.commit()
        flash('Ride started! Safe driving.', 'success')
    return redirect(url_for('driver.ride_detail', ride_id=ride.id))


# ── Complete Ride ──────────────────────────────────────────────────────────────
@driver_bp.route('/complete-ride/<int:ride_id>', methods=['POST'])
@login_required
@driver_required
def complete_ride(ride_id):
    ride = Ride.query.filter_by(id=ride_id, driver_id=current_user.id).first_or_404()
    if ride.status == 'in_progress':
        ride.status = 'completed'
        ride.completed_at = datetime.utcnow()
        ride.actual_fare = ride.estimated_fare - ride.discount_amount

        current_user.is_available = True
        current_user.total_rides += 1
        current_user.total_earnings += (ride.actual_fare or 0)
        db.session.commit()
        flash('Ride completed! Great job.', 'success')
    return redirect(url_for('driver.dashboard'))


# ── Ride Detail ────────────────────────────────────────────────────────────────
@driver_bp.route('/ride/<int:ride_id>')
@login_required
@driver_required
def ride_detail(ride_id):
    ride = Ride.query.filter_by(id=ride_id, driver_id=current_user.id).first_or_404()
    return render_template('driver/ride_detail.html', ride=ride)


# ── Ride History ───────────────────────────────────────────────────────────────
@driver_bp.route('/ride-history')
@login_required
@driver_required
def ride_history():
    page = request.args.get('page', 1, type=int)
    rides = Ride.query.filter_by(driver_id=current_user.id)\
        .order_by(Ride.booked_at.desc()).paginate(page=page, per_page=10)
    return render_template('driver/ride_history.html', rides=rides)


# ── Earnings ───────────────────────────────────────────────────────────────────
@driver_bp.route('/earnings')
@login_required
@driver_required
def earnings():
    # Monthly earnings for chart
    from sqlalchemy import extract
    monthly = []
    for month in range(1, 13):
        total = db.session.query(db.func.sum(Payment.amount))\
            .join(Ride)\
            .filter(Ride.driver_id == current_user.id,
                    extract('month', Payment.paid_at) == month,
                    extract('year', Payment.paid_at) == datetime.utcnow().year).scalar() or 0
        monthly.append(round(total, 2))

    reviews = Review.query.filter_by(driver_id=current_user.id)\
        .order_by(Review.created_at.desc()).limit(10).all()

    return render_template('driver/earnings.html',
                           monthly_earnings=monthly,
                           reviews=reviews)


# ── Toggle Availability ────────────────────────────────────────────────────────
@driver_bp.route('/toggle-availability', methods=['POST'])
@login_required
@driver_required
def toggle_availability():
    current_user.is_available = not current_user.is_available
    db.session.commit()
    status = 'online' if current_user.is_available else 'offline'
    flash(f'You are now {status}.', 'info')
    return redirect(url_for('driver.dashboard'))


# ── Profile ────────────────────────────────────────────────────────────────────
@driver_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@driver_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name).strip()
        current_user.phone = request.form.get('phone', current_user.phone).strip()
        current_user.vehicle_model = request.form.get('vehicle_model', current_user.vehicle_model)
        current_user.vehicle_color = request.form.get('vehicle_color', current_user.vehicle_color)
        new_pass = request.form.get('new_password', '')
        if new_pass and len(new_pass) >= 6:
            current_user.set_password(new_pass)
        db.session.commit()
        flash('Profile updated.', 'success')
    return render_template('driver/profile.html')