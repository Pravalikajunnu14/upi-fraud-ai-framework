"""
validators.py
-----
Request data validation and sanitization for the UPI Fraud Detection API.
Provides utility functions and decorators for input validation.
"""

import re
from functools import wraps
from flask import request, jsonify


# ─── Type Conversion Helpers ──────────────────────────────────────────────────

def safe_int(val, default=0, min_val=None, max_val=None):
    """
    Safely convert value to int with optional range validation.
    
    Args:
        val: Value to convert (can be str, int, or None)
        default: Default value if conversion fails
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
    
    Returns:
        int or default value
    
    Raises:
        ValueError: If value is outside min/max range
    """
    try:
        if val is None:
            return default
        result = int(val)
        
        if min_val is not None and result < min_val:
            raise ValueError(f"Value {result} is below minimum {min_val}")
        if max_val is not None and result > max_val:
            raise ValueError(f"Value {result} exceeds maximum {max_val}")
            
        return result
    except (ValueError, TypeError):
        if min_val is not None or max_val is not None:
            raise ValueError(f"Invalid integer: {val}")
        return default


def safe_float(val, default=0.0, min_val=None, max_val=None):
    """
    Safely convert value to float with optional range validation.
    
    Args:
        val: Value to convert (can be str, float, or None)
        default: Default value if conversion fails
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
    
    Returns:
        float or default value
    
    Raises:
        ValueError: If value is outside min/max range or not a finite number
    """
    try:
        if val is None:
            return default
        
        result = float(val)
        
        # Check for NaN or Infinity
        if not (-1e308 < result < 1e308):
            raise ValueError(f"Value {result} is not finite")
        
        if min_val is not None and result < min_val:
            raise ValueError(f"Value {result} is below minimum {min_val}")
        if max_val is not None and result > max_val:
            raise ValueError(f"Value {result} exceeds maximum {max_val}")
            
        return result
    except (ValueError, TypeError):
        if min_val is not None or max_val is not None:
            raise ValueError(f"Invalid float: {val}")
        return default


def safe_string(val, default="", max_length=None, pattern=None):
    """
    Safely convert value to string with sanitization.
    
    Args:
        val: Value to convert
        default: Default if None
        max_length: Maximum allowed length
        pattern: Regex pattern for validation (if provided, value must match)
    
    Returns:
        str or default
    
    Raises:
        ValueError: If validation fails
    """
    if val is None:
        return default
    
    try:
        result = str(val).strip()
        
        if max_length and len(result) > max_length:
            raise ValueError(f"String exceeds max length of {max_length}")
        
        if pattern and not re.match(pattern, result):
            raise ValueError(f"String does not match required pattern")
        
        return result
    except Exception as e:
        raise ValueError(f"Invalid string: {str(e)}")


# ─── Transaction Validation ──────────────────────────────────────────────────

def validate_transaction_amount(amount, min_amount=1, max_amount=500000):
    """
    Validate transaction amount.
    
    Args:
        amount: Amount to validate (can be string or number)
        min_amount: Minimum allowed amount (INR)
        max_amount: Maximum allowed amount (INR)
    
    Returns:
        float: Validated amount
    
    Raises:
        ValueError: If validation fails
    """
    try:
        val = safe_float(amount, min_val=min_amount, max_val=max_amount)
        if val == 0 and amount is not None:
            raise ValueError(f"Amount must be between {min_amount} and {max_amount}")
        return val
    except ValueError as e:
        raise ValueError(f"Invalid amount: {str(e)}")


def validate_hour(hour, min_hour=0, max_hour=23):
    """
    Validate hour of transaction (0-23).
    
    Args:
        hour: Hour value
        min_hour: Minimum (default 0)
        max_hour: Maximum (default 23)
    
    Returns:
        int: Validated hour
    
    Raises:
        ValueError: If hour is out of range
    """
    try:
        val = safe_int(hour, min_val=min_hour, max_val=max_hour)
        if hour is not None and (val < min_hour or val > max_hour):
            raise ValueError(f"Hour must be between {min_hour} and {max_hour}")
        return val
    except ValueError as e:
        raise ValueError(f"Invalid hour: {str(e)}")


def validate_day_of_week(day, min_day=0, max_day=6):
    """
    Validate day of week (0=Monday, 6=Sunday).
    
    Args:
        day: Day value
        min_day: Minimum (default 0)
        max_day: Maximum (default 6)
    
    Returns:
        int: Validated day
    
    Raises:
        ValueError: If day is out of range
    """
    try:
        val = safe_int(day, min_val=min_day, max_val=max_day)
        if day is not None and (val < min_day or val > max_day):
            raise ValueError(f"Day of week must be between {min_day} and {max_day}")
        return val
    except ValueError as e:
        raise ValueError(f"Invalid day_of_week: {str(e)}")


def validate_coordinates(latitude, longitude):
    """
    Validate latitude and longitude.
    
    Args:
        latitude: Latitude value (-90 to 90)
        longitude: Longitude value (-180 to 180)
    
    Returns:
        tuple: (validated_lat, validated_lng)
    
    Raises:
        ValueError: If coordinates are invalid
    """
    try:
        lat = safe_float(latitude, min_val=-90.0, max_val=90.0)
        lng = safe_float(longitude, min_val=-180.0, max_val=180.0)
        
        if latitude is not None and (lat < -90.0 or lat > 90.0):
            raise ValueError("Latitude must be between -90 and 90")
        if longitude is not None and (lng < -180.0 or lng > 180.0):
            raise ValueError("Longitude must be between -180 and 180")
        
        return (lat, lng)
    except ValueError as e:
        raise ValueError(f"Invalid coordinates: {str(e)}")


def validate_device_id(device_id, max_length=50):
    """
    Validate device ID (alphanumeric + underscore, max 50 chars).
    
    Args:
        device_id: Device ID string
        max_length: Maximum allowed length
    
    Returns:
        str: Validated device ID
    
    Raises:
        ValueError: If device ID is invalid
    """
    if device_id is None or device_id == "":
        return None
    
    try:
        val = safe_string(device_id, max_length=max_length)
        # Allow alphanumeric, underscore, hyphen, colon
        if not re.match(r"^[a-zA-Z0-9_:\-]+$", val):
            raise ValueError("Device ID must contain only alphanumeric, underscore, hyphen, or colon")
        return val
    except ValueError as e:
        raise ValueError(f"Invalid device_id: {str(e)}")


def validate_upi_id(upi_id, max_length=50):
    """
    Validate UPI ID (basic format check: xxx@bank).
    
    Args:
        upi_id: UPI ID string (e.g., "user@okhdfcbank")
        max_length: Maximum allowed length
    
    Returns:
        str: Validated UPI ID or empty string if not provided
    
    Raises:
        ValueError: If UPI ID format is invalid
    """
    if upi_id is None or upi_id == "":
        return ""
    
    try:
        val = safe_string(upi_id, max_length=max_length).lower()
        # Basic UPI format: handle@provider (allow optional)
        if val and not re.match(r"^[a-z0-9._-]+@[a-z0-9]+$", val):
            raise ValueError("UPI ID should follow format: username@provider")
        return val
    except ValueError as e:
        raise ValueError(f"Invalid upi_id: {str(e)}")


def validate_city(city, valid_cities):
    """
    Validate that city is in the allowed list.
    
    Args:
        city: City name
        valid_cities: List/dict of valid city names
    
    Returns:
        str: Validated city name
    
    Raises:
        ValueError: If city is not valid
    """
    if city is None:
        city = "Mumbai"
    
    city = str(city).strip()
    
    # valid_cities could be list or dict (dict.keys())
    if isinstance(valid_cities, dict):
        city_list = valid_cities.keys()
    else:
        city_list = valid_cities
    
    if city not in city_list:
        raise ValueError(f"City '{city}' not supported. Valid cities: {', '.join(sorted(city_list))}")
    
    return city


def validate_transaction_frequency(freq, min_freq=1, max_freq=100):
    """
    Validate transaction frequency (number of transactions).
    
    Args:
        freq: Frequency value
        min_freq: Minimum (default 1)
        max_freq: Maximum (default 100)
    
    Returns:
        int: Validated frequency
    
    Raises:
        ValueError: If out of range
    """
    try:
        val = safe_int(freq, default=1, min_val=min_freq, max_val=max_freq)
        if freq is not None and (val < min_freq or val > max_freq):
            raise ValueError(f"Frequency must be between {min_freq} and {max_freq}")
        return val
    except ValueError as e:
        raise ValueError(f"Invalid transaction_frequency: {str(e)}")


# ─── Pagination Validation ───────────────────────────────────────────────────

def validate_pagination(page=1, limit=20, max_limit=1000):
    """
    Validate pagination parameters.
    
    Args:
        page: Page number (1-indexed)
        limit: Results per page
        max_limit: Maximum allowed results per page
    
    Returns:
        tuple: (validated_page, validated_limit, offset)
    
    Raises:
        ValueError: If values are invalid
    """
    try:
        page = safe_int(page, default=1, min_val=1)
        limit = safe_int(limit, default=20, min_val=1, max_val=max_limit)
        
        offset = (page - 1) * limit
        return (page, limit, offset)
    except ValueError as e:
        raise ValueError(f"Invalid pagination: {str(e)}")


# ─── Decorator: Validate Request JSON ────────────────────────────────────────

def validate_request_json(required_fields=None, optional_fields=None):
    """
    Decorator to validate required fields in JSON request body.
    
    Args:
        required_fields: List of field names that must be present
        optional_fields: List of field names that are optional
    
    Usage:
        @app.route('/endpoint', methods=['POST'])
        @validate_request_json(required_fields=['amount', 'city'])
        def my_endpoint():
            data = request.get_json()  # Already validated
            ...
    """
    if required_fields is None:
        required_fields = []
    if optional_fields is None:
        optional_fields = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "Request body must be valid JSON"}), 400
            
            # Check required fields
            missing_fields = [f for f in required_fields if f not in data or data[f] is None]
            if missing_fields:
                return jsonify({
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }), 400
            
            # Store validated data in request context for use in the route function
            request.validated_data = data
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ─── Decorator: Validate Query Parameters ────────────────────────────────────

def validate_query_params(params_spec):
    """
    Decorator to validate query parameters.
    
    Args:
        params_spec: Dict of param_name -> {type, required, default, validator_func}
    
    Usage:
        @validate_query_params({
            'limit': {'type': int, 'required': False, 'default': 20},
            'offset': {'type': int, 'required': False, 'default': 0}
        })
        def my_endpoint():
            limit = request.validated_params['limit']
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            validated_params = {}
            
            for param_name, spec in params_spec.items():
                value = request.args.get(param_name)
                param_type = spec.get('type', str)
                is_required = spec.get('required', False)
                default = spec.get('default')
                custom_validator = spec.get('validator')
                
                if value is None:
                    if is_required:
                        return jsonify({
                            "error": f"Missing required query parameter: {param_name}"
                        }), 400
                    validated_params[param_name] = default
                    continue
                
                # Type conversion with validation
                try:
                    if param_type == int:
                        min_val = spec.get('min')
                        max_val = spec.get('max')
                        validated_params[param_name] = safe_int(value, min_val=min_val, max_val=max_val)
                    elif param_type == float:
                        min_val = spec.get('min')
                        max_val = spec.get('max')
                        validated_params[param_name] = safe_float(value, min_val=min_val, max_val=max_val)
                    else:
                        validated_params[param_name] = param_type(value)
                    
                    # Apply custom validator if provided
                    if custom_validator:
                        validated_params[param_name] = custom_validator(validated_params[param_name])
                
                except (ValueError, TypeError) as e:
                    return jsonify({
                        "error": f"Invalid {param_name}: {str(e)}"
                    }), 400
            
            request.validated_params = validated_params
            return func(*args, **kwargs)
        return wrapper
    return decorator
