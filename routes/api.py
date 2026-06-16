"""
RideNow - REST API Routes
JSON endpoints for fare estimation, promo validation, ride status polling
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models.models import db, Ride, PromoCode, Driver
from datetime import datetime
import math

api_bp = Blueprint('api', __name__)


# Fare per km by vehicle type (₹)
FARE_RATES = {
    'bike': {'base': 15, 'per_km': 8, 'label': 'Bike', 'icon': '🏍️'},
    'auto': {'base': 20, 'per_km': 12, 'label': 'Auto', 'icon': '🛺'},
    'mini': {'base': 30, 'per_km': 14, 'label': 'Mini Cab', 'icon': '🚗'},
    'sedan': {'base': 50, 'per_km': 18, 'label': 'Sedan', 'icon': '🚙'},
    'suv': {'base': 80, 'per_km': 22, 'label': 'SUV', 'icon': '🚐'},
}


def haversine(lat1, lng1, lat2, lng2):
    """Calculate distance in km between two coordinates"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@api_bp.route('/estimate-fare', methods=['POST'])
def estimate_fare():
    """Return fare estimates for all vehicle types"""
    data = request.get_json()
    plat = float(data.get('pickup_lat', 0))
    plng = float(data.get('pickup_lng', 0))
    dlat = float(data.get('drop_lat', 0))
    dlng = float(data.get('drop_lng', 0))

    if not all([plat, plng, dlat, dlng]):
        # Fallback demo distance
        distance = 8.5
    else:
        distance = haversine(plat, plng, dlat, dlng)
        distance = max(distance, 1.0)

    estimates = {}
    for vtype, rates in FARE_RATES.items():
        fare = rates['base'] + (distance * rates['per_km'])
        # Surge pricing simulation (20% surge during peak hours)
        hour = datetime.utcnow().hour
        if 8 <= hour <= 10 or 17 <= hour <= 20:
            fare *= 1.2
        estimates[vtype] = {
            'label': rates['label'],
            'icon': rates['icon'],
            'fare': round(fare, 2),
            'distance': round(distance, 1),
            'eta': f"{int(distance * 3 + 5)} mins",
        }

    return jsonify({'success': True, 'estimates': estimates, 'distance': round(distance, 1)})


@api_bp.route('/validate-promo', methods=['POST'])
@login_required
def validate_promo():
    """Validate a promo code and return discount amount"""
    data = request.get_json()
    code = data.get('code', '').upper()
    fare = float(data.get('fare', 0))

    promo = PromoCode.query.filter_by(code=code, is_active=True).first()
    if not promo:
        return jsonify({'success': False, 'message': 'Invalid or expired promo code.'})
    if promo.valid_until and promo.valid_until < datetime.utcnow():
        return jsonify({'success': False, 'message': 'Promo code has expired.'})
    if promo.usage_limit and promo.used_count >= promo.usage_limit:
        return jsonify({'success': False, 'message': 'Promo code usage limit reached.'})
    if fare < promo.min_fare:
        return jsonify({'success': False,
                        'message': f'Minimum fare of ₹{promo.min_fare} required.'})

    if promo.discount_type == 'percent':
        discount = fare * promo.discount_value / 100
        if promo.max_discount:
            discount = min(discount, promo.max_discount)
    else:
        discount = promo.discount_value

    return jsonify({
        'success': True,
        'discount': round(discount, 2),
        'final_fare': round(fare - discount, 2),
        'message': f'Promo applied! You save ₹{discount:.2f}'
    })


@api_bp.route('/ride-status/<int:ride_id>')
@login_required
def ride_status(ride_id):
    """Poll ride status (for live tracking simulation)"""
    ride = Ride.query.get_or_404(ride_id)
    driver_data = None
    if ride.driver:
        import random
        # Simulate driver moving toward pickup
        driver_data = {
            'name': ride.driver.name,
            'phone': ride.driver.phone,
            'vehicle': f"{ride.driver.vehicle_model} ({ride.driver.vehicle_color})",
            'vehicle_number': ride.driver.vehicle_number,
            'rating': ride.driver.rating,
            'lat': (ride.driver.current_lat or 19.0760) + random.uniform(-0.001, 0.001),
            'lng': (ride.driver.current_lng or 72.8777) + random.uniform(-0.001, 0.001),
        }
    return jsonify({
        'status': ride.status,
        'driver': driver_data,
        'pickup': ride.pickup_address,
        'drop': ride.drop_address,
    })


@api_bp.route('/available-drivers')
def available_drivers():
    """Return nearby available drivers for map display"""
    import random
    drivers = Driver.query.filter_by(is_available=True, is_verified=True).all()
    result = [{
        'id': d.id,
        'name': d.name,
        'vehicle_type': d.vehicle_type,
        'vehicle_number': d.vehicle_number,
        'rating': d.rating,
        'lat': (d.current_lat or 19.0760) + random.uniform(-0.02, 0.02),
        'lng': (d.current_lng or 72.8777) + random.uniform(-0.02, 0.02),
    } for d in drivers[:10]]
    return jsonify({'drivers': result})