"""
RideNow - Database Models
Defines all SQLAlchemy ORM models for the application
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for ride customers"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    profile_pic = db.Column(db.String(200), default='default_user.png')
    is_active = db.Column(db.Boolean, default=True)
    is_blocked = db.Column(db.Boolean, default=False)
    promo_credits = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(256), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    # Relationships
    rides = db.relationship('Ride', backref='user', lazy=True, foreign_keys='Ride.user_id')
    reviews = db.relationship('Review', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'


class Driver(UserMixin, db.Model):
    """Driver model for ride providers"""
    __tablename__ = 'drivers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    profile_pic = db.Column(db.String(200), default='default_driver.png')
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    vehicle_number = db.Column(db.String(20), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(20), nullable=False)  # bike, auto, mini, sedan, suv
    vehicle_model = db.Column(db.String(100), nullable=False)
    vehicle_color = db.Column(db.String(50), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=5.0)
    total_rides = db.Column(db.Integer, default=0)
    total_earnings = db.Column(db.Float, default=0.0)
    current_lat = db.Column(db.Float, nullable=True)
    current_lng = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(256), nullable=True)

    # Relationships
    rides = db.relationship('Ride', backref='driver', lazy=True, foreign_keys='Ride.driver_id')
    reviews = db.relationship('Review', backref='driver', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"driver_{self.id}"

    def __repr__(self):
        return f'<Driver {self.email}>'


class Admin(UserMixin, db.Model):
    """Admin model for platform management"""
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"admin_{self.id}"

    def __repr__(self):
        return f'<Admin {self.email}>'


class Ride(db.Model):
    """Ride booking model"""
    __tablename__ = 'rides'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)

    # Location details
    pickup_address = db.Column(db.String(300), nullable=False)
    drop_address = db.Column(db.String(300), nullable=False)
    pickup_lat = db.Column(db.Float, nullable=True)
    pickup_lng = db.Column(db.Float, nullable=True)
    drop_lat = db.Column(db.Float, nullable=True)
    drop_lng = db.Column(db.Float, nullable=True)

    # Ride details
    vehicle_type = db.Column(db.String(20), nullable=False)
    distance_km = db.Column(db.Float, nullable=True)
    estimated_fare = db.Column(db.Float, nullable=False)
    actual_fare = db.Column(db.Float, nullable=True)
    promo_code = db.Column(db.String(20), nullable=True)
    discount_amount = db.Column(db.Float, default=0.0)

    # Status: pending, accepted, in_progress, completed, cancelled
    status = db.Column(db.String(20), default='pending')
    cancel_reason = db.Column(db.String(200), nullable=True)

    # Timestamps
    booked_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    payment = db.relationship('Payment', backref='ride', uselist=False, lazy=True)
    review = db.relationship('Review', backref='ride', uselist=False, lazy=True)

    def __repr__(self):
        return f'<Ride {self.id} - {self.status}>'


class Payment(db.Model):
    """Payment records model"""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('rides.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # cash, upi, card
    payment_status = db.Column(db.String(20), default='pending')  # pending, completed, failed, refunded
    transaction_id = db.Column(db.String(100), nullable=True)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Payment {self.id} - {self.payment_status}>'


class Review(db.Model):
    """Driver review and rating model"""
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('rides.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Review {self.id} - {self.rating} stars>'


class PromoCode(db.Model):
    """Promotional codes model"""
    __tablename__ = 'promo_codes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    discount_type = db.Column(db.String(10), nullable=False)  # percent, flat
    discount_value = db.Column(db.Float, nullable=False)
    max_discount = db.Column(db.Float, nullable=True)
    min_fare = db.Column(db.Float, default=0.0)
    usage_limit = db.Column(db.Integer, nullable=True)
    used_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    valid_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PromoCode {self.code}>'