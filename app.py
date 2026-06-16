"""
RideNow - Smart Ride Booking Platform
Main application entry point
"""

import os
from flask import Flask  # pyright: ignore[reportMissingImports]
from flask_login import LoginManager  # pyright: ignore[reportMissingImports]
from models.models import db, User, Driver, Admin
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]

# Load environment variables
load_dotenv()


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)

    # ── Configuration ──────────────────────────────────────────────────────────
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ridenow-secret-key-2024-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///ridenow.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'images')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

    # Mail config (update with real SMTP for production)
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')

    # ── Extensions ─────────────────────────────────────────────────────────────
    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.login_message = 'Please log in to access this page.'

    @login_manager.user_loader
    def load_user(user_id):
        """Load user from session — supports User, Driver, Admin roles"""
        if user_id.startswith('driver_'):
            return Driver.query.get(int(user_id.split('_')[1]))
        elif user_id.startswith('admin_'):
            return Admin.query.get(int(user_id.split('_')[1]))
        return User.query.get(int(user_id))

    # ── Blueprints ─────────────────────────────────────────────────────────────
    from routes.auth import auth_bp
    from routes.user import user_bp
    from routes.driver import driver_bp
    from routes.admin import admin_bp
    from routes.pages import pages_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(driver_bp, url_prefix='/driver')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # ── Database init ──────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        seed_initial_data()

    return app


def seed_initial_data():
    """Seed the database with initial admin and sample data"""
    from models.models import Admin, User, Driver, PromoCode, Ride, Payment, Review
    from datetime import datetime, timedelta
    import random

    # Create default admin if not exists
    if not Admin.query.filter_by(email='admin@ridenow.com').first():
        admin = Admin(name='Super Admin', email='admin@ridenow.com')
        admin.set_password('Admin@123')
        db.session.add(admin)

    # Sample users
    sample_users = [
        ('Rahul Sharma', 'rahul@example.com', '9876543210'),
        ('Priya Patel', 'priya@example.com', '9876543211'),
        ('Amit Kumar', 'amit@example.com', '9876543212'),
        ('Sneha Singh', 'sneha@example.com', '9876543213'),
        ('Vikram Mehta', 'vikram@example.com', '9876543214'),
    ]
    created_users = []
    for name, email, phone in sample_users:
        if not User.query.filter_by(email=email).first():
            u = User(name=name, email=email, phone=phone)
            u.set_password('User@123')
            db.session.add(u)
            created_users.append(u)

    # Sample drivers
    vehicle_types = ['bike', 'auto', 'mini', 'sedan', 'suv']
    vehicle_models = {
        'bike': ['Honda Activa', 'Bajaj Pulsar', 'Royal Enfield'],
        'auto': ['Bajaj RE', 'Piaggio Ape', 'TVS King'],
        'mini': ['Maruti Suzuki Alto', 'Hyundai Santro', 'Tata Nano'],
        'sedan': ['Toyota Etios', 'Honda Amaze', 'Maruti Dzire'],
        'suv': ['Toyota Fortuner', 'Hyundai Creta', 'Mahindra XUV500'],
    }
    colors = ['White', 'Black', 'Silver', 'Red', 'Blue']
    sample_drivers = [
        ('Rajesh Verma', 'rajesh@driver.com', '8765432100', 'DL001', 'MH01AB1234', 'sedan'),
        ('Suresh Nair', 'suresh@driver.com', '8765432101', 'DL002', 'MH02CD5678', 'suv'),
        ('Mohan Das', 'mohan@driver.com', '8765432102', 'DL003', 'MH03EF9012', 'auto'),
        ('Arjun Singh', 'arjun@driver.com', '8765432103', 'DL004', 'MH04GH3456', 'mini'),
        ('Kavya Reddy', 'kavya@driver.com', '8765432104', 'DL005', 'MH05IJ7890', 'bike'),
    ]
    created_drivers = []
    for name, email, phone, lic, vnum, vtype in sample_drivers:
        if not Driver.query.filter_by(email=email).first():
            d = Driver(
                name=name, email=email, phone=phone,
                license_number=lic, vehicle_number=vnum,
                vehicle_type=vtype,
                vehicle_model=random.choice(vehicle_models[vtype]),
                vehicle_color=random.choice(colors),
                is_verified=True,
                rating=round(random.uniform(3.8, 5.0), 1),
                total_rides=random.randint(50, 500),
                total_earnings=round(random.uniform(5000, 50000), 2),
                current_lat=19.0760 + random.uniform(-0.1, 0.1),
                current_lng=72.8777 + random.uniform(-0.1, 0.1),
            )
            d.set_password('Driver@123')
            db.session.add(d)
            created_drivers.append(d)

    # Promo codes
    promo_codes = [
        ('FIRST50', 'percent', 50, 100, 0, 1000, True),
        ('RIDE20', 'percent', 20, 80, 50, 500, True),
        ('FLAT30', 'flat', 30, None, 100, 200, True),
        ('WELCOME', 'percent', 30, 60, 0, None, True),
    ]
    for code, dtype, dval, maxd, minf, ulim, active in promo_codes:
        if not PromoCode.query.filter_by(code=code).first():
            p = PromoCode(
                code=code, discount_type=dtype, discount_value=dval,
                max_discount=maxd, min_fare=minf, usage_limit=ulim,
                is_active=active, valid_until=datetime.utcnow() + timedelta(days=365)
            )
            db.session.add(p)

    db.session.commit()

    # Seed rides only if we have users and drivers in DB
    all_users = User.query.all()
    all_drivers = Driver.query.all()
    if all_users and all_drivers and Ride.query.count() == 0:
        locations = [
            ('Mumbai Airport', 'Bandra West', 19.0896, 72.8656, 19.0544, 72.8402),
            ('Dadar Station', 'Andheri East', 19.0178, 72.8478, 19.1136, 72.8697),
            ('Colaba', 'Powai', 18.9067, 72.8147, 19.1177, 72.9060),
            ('Thane', 'Borivali', 19.2183, 72.9781, 19.2307, 72.8567),
            ('Navi Mumbai', 'Churchgate', 19.0330, 73.0297, 18.9355, 72.8276),
        ]
        statuses = ['completed', 'completed', 'completed', 'cancelled', 'completed']
        vehicle_types_list = ['bike', 'auto', 'mini', 'sedan', 'suv']
        fare_map = {'bike': 8, 'auto': 12, 'mini': 14, 'sedan': 18, 'suv': 22}

        for i, (pu, dr, plat, plng, dlat, dlng) in enumerate(locations):
            user = all_users[i % len(all_users)]
            driver = all_drivers[i % len(all_drivers)]
            vtype = vehicle_types_list[i % len(vehicle_types_list)]
            distance = round(random.uniform(3, 20), 1)
            fare = round(distance * fare_map[vtype] + random.uniform(20, 50), 2)
            status = statuses[i]
            booked = datetime.utcnow() - timedelta(days=random.randint(1, 30))

            ride = Ride(
                user_id=user.id, driver_id=driver.id,
                pickup_address=pu, drop_address=dr,
                pickup_lat=plat, pickup_lng=plng,
                drop_lat=dlat, drop_lng=dlng,
                vehicle_type=vtype, distance_km=distance,
                estimated_fare=fare, actual_fare=fare if status == 'completed' else None,
                status=status, booked_at=booked,
                accepted_at=booked + timedelta(minutes=2) if status != 'cancelled' else None,
                completed_at=booked + timedelta(minutes=int(distance * 3)) if status == 'completed' else None,
            )
            db.session.add(ride)
            db.session.flush()

            if status == 'completed':
                pay = Payment(
                    ride_id=ride.id, user_id=user.id, amount=fare,
                    payment_method=random.choice(['cash', 'upi', 'card']),
                    payment_status='completed',
                    transaction_id=f'TXN{ride.id:06d}',
                )
                db.session.add(pay)

                rev = Review(
                    ride_id=ride.id, user_id=user.id, driver_id=driver.id,
                    rating=random.randint(3, 5),
                    comment=random.choice([
                        'Great ride!', 'Very punctual.', 'Clean vehicle.',
                        'Polite driver.', 'Smooth experience.'
                    ])
                )
                db.session.add(rev)

        db.session.commit()


# ── Entry point ────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)