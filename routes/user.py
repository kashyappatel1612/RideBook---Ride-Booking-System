"""
RideNow - User Routes
Dashboard, booking, ride history, profile management for customers
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from models.models import db, User, Driver, Ride, Payment, Review, PromoCode
from datetime import datetime
from functools import wraps

user_bp = Blueprint('user', __name__)


def user_required(f):
    """Decorator to ensure the logged-in entity is a User"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not isinstance(current_user._get_current_object(), User):
            flash('Access restricted to users.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ──────────────────────────────────────────────────────────────────
@user_bp.route('/dashboard')
@login_required
@user_required
def dashboard():
    recent_rides = Ride.query.filter_by(user_id=current_user.id)\
        .order_by(Ride.booked_at.desc()).limit(5).all()
    total_rides = Ride.query.filter_by(user_id=current_user.id).count()
    completed = Ride.query.filter_by(user_id=current_user.id, status='completed').count()
    total_spent = db.session.query(db.func.sum(Payment.amount))\
        .filter_by(user_id=current_user.id).scalar() or 0

    return render_template('user/dashboard.html',
                           recent_rides=recent_rides,
                           total_rides=total_rides,
                           completed_rides=completed,
                           total_spent=round(total_spent, 2))


# ── Book a Ride ────────────────────────────────────────────────────────────────
@user_bp.route('/book-ride', methods=['GET', 'POST'])
@login_required
@user_required
def book_ride():
    if request.method == 'POST':
        pickup = request.form.get('pickup_address', '').strip()
        drop = request.form.get('drop_address', '').strip()
        vehicle_type = request.form.get('vehicle_type', '')
        estimated_fare = request.form.get('estimated_fare', 0)
        distance_km = request.form.get('distance_km', 0)
        pickup_lat = request.form.get('pickup_lat', 0)
        pickup_lng = request.form.get('pickup_lng', 0)
        drop_lat = request.form.get('drop_lat', 0)
        drop_lng = request.form.get('drop_lng', 0)
        promo_code = request.form.get('promo_code', '').strip().upper()
        payment_method = request.form.get('payment_method', 'cash')

        if not all([pickup, drop, vehicle_type]):
            flash('Please fill in all booking details.', 'danger')
            return render_template('user/book_ride.html')

        discount = 0.0
        if promo_code:
            promo = PromoCode.query.filter_by(code=promo_code, is_active=True).first()
            if promo:
                fare = float(estimated_fare)
                if promo.discount_type == 'percent':
                    discount = (fare * promo.discount_value / 100)
                    if promo.max_discount:
                        discount = min(discount, promo.max_discount)
                else:
                    discount = promo.discount_value
                promo.used_count += 1
            else:
                flash('Invalid or expired promo code.', 'warning')

        # Find an available driver with matching vehicle type
        driver = Driver.query.filter_by(
            vehicle_type=vehicle_type, is_available=True, is_verified=True, is_blocked=False
        ).first()

        ride = Ride(
            user_id=current_user.id,
            driver_id=driver.id if driver else None,
            pickup_address=pickup, drop_address=drop,
            pickup_lat=float(pickup_lat or 0), pickup_lng=float(pickup_lng or 0),
            drop_lat=float(drop_lat or 0), drop_lng=float(drop_lng or 0),
            vehicle_type=vehicle_type,
            distance_km=float(distance_km or 0),
            estimated_fare=float(estimated_fare or 0),
            promo_code=promo_code if promo_code else None,
            discount_amount=discount,
            status='accepted' if driver else 'pending',
        )
        db.session.add(ride)
        if driver:
            driver.is_available = False
        db.session.commit()

        if payment_method in ['upi', 'card']:
            return redirect(url_for('user.payment', ride_id=ride.id,
                                    method=payment_method, amount=float(estimated_fare) - discount))

        flash('Ride booked successfully! Your driver is on the way.', 'success')
        return redirect(url_for('user.ride_status', ride_id=ride.id))

    return render_template('user/book_ride.html')


# ── Ride Status ────────────────────────────────────────────────────────────────
@user_bp.route('/ride/<int:ride_id>')
@login_required
@user_required
def ride_status(ride_id):
    ride = Ride.query.filter_by(id=ride_id, user_id=current_user.id).first_or_404()
    return render_template('user/ride_status.html', ride=ride)


# ── Ride History ───────────────────────────────────────────────────────────────
@user_bp.route('/ride-history')
@login_required
@user_required
def ride_history():
    page = request.args.get('page', 1, type=int)
    rides = Ride.query.filter_by(user_id=current_user.id)\
        .order_by(Ride.booked_at.desc()).paginate(page=page, per_page=10)
    return render_template('user/ride_history.html', rides=rides)


# ── Cancel Ride ────────────────────────────────────────────────────────────────
@user_bp.route('/cancel-ride/<int:ride_id>', methods=['POST'])
@login_required
@user_required
def cancel_ride(ride_id):
    ride = Ride.query.filter_by(id=ride_id, user_id=current_user.id).first_or_404()
    if ride.status in ['pending', 'accepted']:
        reason = request.form.get('reason', 'Cancelled by user')
        ride.status = 'cancelled'
        ride.cancel_reason = reason
        if ride.driver:
            ride.driver.is_available = True
        db.session.commit()
        flash('Ride cancelled successfully.', 'info')
    else:
        flash('This ride cannot be cancelled.', 'warning')
    return redirect(url_for('user.ride_history'))


# ── Payment page ───────────────────────────────────────────────────────────────
@user_bp.route('/payment/<int:ride_id>')
@login_required
@user_required
def payment(ride_id):
    ride = Ride.query.filter_by(id=ride_id, user_id=current_user.id).first_or_404()
    method = request.args.get('method', 'upi')
    amount = request.args.get('amount', ride.estimated_fare - ride.discount_amount)
    return render_template('user/payment.html', ride=ride, method=method, amount=float(amount))


# ── Confirm Payment ────────────────────────────────────────────────────────────
@user_bp.route('/confirm-payment/<int:ride_id>', methods=['POST'])
@login_required
@user_required
def confirm_payment(ride_id):
    ride = Ride.query.filter_by(id=ride_id, user_id=current_user.id).first_or_404()
    method = request.form.get('method', 'cash')
    amount = float(request.form.get('amount', ride.estimated_fare))

    pay = Payment(
        ride_id=ride.id, user_id=current_user.id,
        amount=amount, payment_method=method,
        payment_status='completed',
        transaction_id=f'TXN{ride.id:06d}{int(datetime.utcnow().timestamp())}',
    )
    db.session.add(pay)
    db.session.commit()
    flash('Payment successful!', 'success')
    return redirect(url_for('user.ride_status', ride_id=ride.id))


# ── Submit Review ──────────────────────────────────────────────────────────────
@user_bp.route('/review/<int:ride_id>', methods=['GET', 'POST'])
@login_required
@user_required
def submit_review(ride_id):
    ride = Ride.query.filter_by(id=ride_id, user_id=current_user.id, status='completed').first_or_404()
    if ride.review:
        flash('You already reviewed this ride.', 'info')
        return redirect(url_for('user.ride_history'))

    if request.method == 'POST':
        rating = int(request.form.get('rating', 5))
        comment = request.form.get('comment', '').strip()
        review = Review(
            ride_id=ride.id, user_id=current_user.id,
            driver_id=ride.driver_id, rating=rating, comment=comment
        )
        db.session.add(review)

        # Update driver's average rating
        if ride.driver:
            all_reviews = Review.query.filter_by(driver_id=ride.driver_id).all()
            avg = sum(r.rating for r in all_reviews) / len(all_reviews) if all_reviews else rating
            ride.driver.rating = round(avg, 1)

        db.session.commit()
        flash('Thank you for your review!', 'success')
        return redirect(url_for('user.ride_history'))

    return render_template('user/review.html', ride=ride)


# ── Profile ────────────────────────────────────────────────────────────────────
@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@user_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name).strip()
        current_user.phone = request.form.get('phone', current_user.phone).strip()
        new_pass = request.form.get('new_password', '')
        if new_pass:
            if len(new_pass) < 6:
                flash('Password must be at least 6 characters.', 'danger')
                return render_template('user/profile.html')
            current_user.set_password(new_pass)
        db.session.commit()
        flash('Profile updated successfully.', 'success')
    return render_template('user/profile.html')