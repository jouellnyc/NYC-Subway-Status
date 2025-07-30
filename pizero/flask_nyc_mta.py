
#!/usr/bin/env python3
"""
Lightweight web service for serving transit data to MicroPython clients
Features caching to prevent client timeouts when data fetching is slow
"""

from flask import Flask, jsonify, request
import json
import threading
import time
import logging
import os
from datetime import datetime, timedelta
from werkzeug.serving import WSGIRequestHandler

from mta_pb2 import MTATrainChecker
checker = MTATrainChecker()

app = Flask(__name__)

# Cache configuration
CACHE_DURATION = 600  # Cache data for 600 seconds (10 minutes)
UPDATE_INTERVAL = 480  # Update cache every 480 seconds (8 minutes)

# Global cache variables
cached_data = None
cache_timestamp = None
cache_lock = threading.Lock()
update_thread = None
is_updating = False

def setup_logging():
    """Configure separate logging for Flask web logs and application logs"""

    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Configure application logger
    app_logger = logging.getLogger('transit_app')
    app_logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicates
    app_logger.handlers.clear()

    # Create file handler for application logs
    app_handler = logging.FileHandler('logs/transit_app.log')
    app_handler.setLevel(logging.INFO)

    # Create formatter for application logs
    app_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    app_handler.setFormatter(app_formatter)
    app_logger.addHandler(app_handler)

    # Configure Flask/Werkzeug logger for web requests
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)

    # Remove existing handlers
    werkzeug_logger.handlers.clear()

    # Create file handler for web logs
    web_handler = logging.FileHandler('logs/web_requests.log')
    web_handler.setLevel(logging.INFO)

    # Create formatter for web logs
    web_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    web_handler.setFormatter(web_formatter)
    werkzeug_logger.addHandler(web_handler)

    # Also add console handler for immediate feedback during startup
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(console_formatter)

    app_logger.addHandler(console_handler)

    # Disable Flask's default logger to avoid duplicate console output
    app.logger.handlers.clear()

    return app_logger

# Set up logging
logger = setup_logging()

def fetch_transit_data():
    """
    Fetch fresh transit data - this can take 30+ seconds
    """
    try:
        logger.info("Fetching fresh transit data...")
        raw_data = checker.get_service_status()

        # Normalize the data to expected format
        normalized_data = normalize_mta_data(raw_data)

        if normalized_data:
            normalized_data['last_updated'] = datetime.now().isoformat()
            logger.info("Fresh data retrieved successfully")
            logger.info(f"Train: {normalized_data.get('train')}, Status: {normalized_data.get('status')}")
            return normalized_data
        else:
            logger.warning("MTA checker returned no data")
            return None

    except Exception as e:
        logger.error(f"Error fetching transit data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def update_cache():
    """Update the cache with fresh data"""
    global cached_data, cache_timestamp, is_updating

    with cache_lock:
        is_updating = True

    try:
        logger.info("Fetching fresh transit data...")
        raw_data = checker.get_service_status()

        if raw_data:
            # Create the merged/normalized version for backward compatibility
            normalized_data = normalize_mta_data(raw_data)

            if normalized_data:
                # Store raw data inside the normalized data dictionary
                normalized_data['__raw_data__'] = raw_data

                with cache_lock:
                    cached_data = normalized_data
                    cache_timestamp = datetime.now()
                    logger.info("Cache updated successfully")
                    logger.info(f"Raw data keys: {list(raw_data.keys()) if raw_data else 'None'}")
        else:
            logger.warning("Failed to fetch fresh data, keeping old cache")
    finally:
        with cache_lock:
            is_updating = False

def background_updater():
    """Background thread to periodically update cache"""
    while True:
        try:
            update_cache()
            time.sleep(UPDATE_INTERVAL)
        except Exception as e:
            logger.error(f"Background updater error: {e}")
            time.sleep(10)  # Wait 10 seconds before retrying

def normalize_mta_data(raw_data):
    """Normalize MTA checker data to expected format"""
    if not raw_data:
        logger.warning("MTA checker returned None/empty data")
        return None

    # Debug: Print the entire raw data structure
    logger.info(f"Raw MTA data type: {type(raw_data)}")
    if isinstance(raw_data, dict):
        logger.info(f"Raw MTA data keys: {list(raw_data.keys())}")

    # Initialize normalized data structure
    normalized = {
        "train": "",
        "status": "Good Service",
        "status_type": "normal",
        "active_trips": 0,
        "last_updated": datetime.now().isoformat(),
        "planned_work": [],
        "service_changes": [],
        "delays": []
    }

    # Handle the nested structure where data is organized by train line
    if isinstance(raw_data, dict):
        train_lines = []
        all_alerts = []
        worst_status = "Good Service"

        # Process each train line (R, F, etc.)
        for line_key, line_data in raw_data.items():
            if isinstance(line_data, dict):
                logger.info(f"Processing line {line_key}: {line_data.get('route', 'Unknown')} - {line_data.get('status', 'Unknown')}")

                train_lines.append(line_key)

                # Get status for this line
                line_status = line_data.get('status', 'Good Service')
                if line_status != 'Good Service':
                    worst_status = line_status  # Use the first non-good status we find

                # Process alerts for this line
                alerts = line_data.get('alerts', [])
                logger.info(f"Line {line_key} has {len(alerts)} alerts")

                for alert in alerts:
                    if isinstance(alert, dict):
                        alert_text = alert.get('alert_text', alert.get('description', alert.get('summary', str(alert))))
                        alert_id = alert.get('id', '')

                        # Categorize alerts based on ID or content
                        if 'planned_work' in alert_id or 'construction' in alert_text.lower():
                            normalized["planned_work"].append(f"[{line_key}] {alert_text}")
                        elif 'delay' in alert_id or 'delay' in alert_text.lower():
                            normalized["delays"].append(f"[{line_key}] {alert_text}")
                        else:
                            normalized["service_changes"].append(f"[{line_key}] {alert_text}")

                        logger.info(f"Alert: {alert_text[:100]}...")
                    else:
                        normalized["service_changes"].append(f"[{line_key}] {str(alert)}")

        # Set combined train name and status
        normalized["train"] = "/".join(train_lines) + " TRAINS" if train_lines else "TRAINS"
        normalized["status"] = worst_status

        # Set status type based on status
        if "delay" in worst_status.lower():
            normalized["status_type"] = "delay"
        elif "planned" in worst_status.lower() or "construction" in worst_status.lower():
            normalized["status_type"] = "scheduled_maintenance"
        elif worst_status == "Good Service":
            normalized["status_type"] = "normal"
        else:
            normalized["status_type"] = "service_change"

    logger.info(f"Normalized data - Train: {normalized['train']}, Status: {normalized['status']}")
    logger.info(f"Alerts summary - Delays: {len(normalized['delays'])}, Changes: {len(normalized['service_changes'])}, Planned: {len(normalized['planned_work'])}")

    return normalized

def normalize_single_line_data(line_key, line_data):
    """Normalize data for a single train line"""
    now = datetime.now()

    # Filter alerts to only include currently active ones
    alerts = line_data.get('alerts', [])
    active_alerts = []

    for alert in alerts:
        if isinstance(alert, dict):
            active_periods = alert.get('active_period', [])
            is_currently_active = False

            if not active_periods:
                # No active period specified, assume it's current
                is_currently_active = True
            else:
                # Check if current time falls within any active period
                for period in active_periods:
                    start_time = period.get('start')
                    end_time = period.get('end')

                    # Handle the case where times might be datetime objects or timestamps
                    if start_time and end_time:
                        # If they're already datetime objects, use them directly
                        if isinstance(start_time, datetime) and isinstance(end_time, datetime):
                            if start_time <= now <= end_time:
                                is_currently_active = True
                                break

            if is_currently_active:
                active_alerts.append(alert)
                logger.debug(f"Line {line_key} - ACTIVE alert: {alert.get('header', 'No header')[:100]}...")
            else:
                logger.debug(f"Line {line_key} - SKIPPING future alert: {alert.get('header', 'No header')[:100]}...")

    # Determine actual status based on active alerts
    actual_status = "Good Service"
    if active_alerts:
        # If there are active alerts, use the original status
        actual_status = line_data.get('status', 'Good Service')

    normalized = {
        "train": f"{line_key} TRAIN",
        "line_id": line_key,
        "status": actual_status,
        "status_type": "normal",
        "active_trips": line_data.get('active_trips', 0),
        "last_updated": datetime.now().isoformat(),
        "planned_work": [],
        "service_changes": [],
        "delays": [],
        "total_alerts": len(alerts),
        "active_alerts": len(active_alerts)
    }

    # Set status type based on status
    status = normalized["status"].lower()
    if "delay" in status:
        normalized["status_type"] = "delay"
    elif "planned" in status or "construction" in status:
        normalized["status_type"] = "scheduled_maintenance"
    elif normalized["status"] == "Good Service":
        normalized["status_type"] = "normal"
    else:
        normalized["status_type"] = "service_change"

    # Process only the active alerts
    for alert in active_alerts:
        if isinstance(alert, dict):
            alert_text = alert.get('alert_text', alert.get('description', alert.get('header', str(alert))))
            alert_id = alert.get('id', '')

            # Categorize alerts
            if 'planned_work' in alert_id or 'construction' in alert_text.lower():
                normalized["planned_work"].append(alert_text)
            elif 'delay' in alert_id or 'delay' in alert_text.lower():
                normalized["delays"].append(alert_text)
            else:
                normalized["service_changes"].append(alert_text)
        else:
            normalized["service_changes"].append(str(alert))

    logger.debug(f"Line {line_key} final status: {normalized['status']} (was: {line_data.get('status', 'Unknown')})")

    return normalized

def get_cached_data():
    """Get data from cache, with fallback logic"""
    global cached_data, cache_timestamp

    try:
        with cache_lock:
            now = datetime.now()

            # If we have cached data and it's not too old, return it
            if cached_data and cache_timestamp:
                age = (now - cache_timestamp).total_seconds()
                if age < CACHE_DURATION:
                    return cached_data, f"cached ({int(age)}s old)"

            # If cache is stale but we're currently updating, return stale data
            if cached_data and is_updating:
                age = (now - cache_timestamp).total_seconds() if cache_timestamp else 999
                return cached_data, f"stale but updating ({int(age)}s old)"

            # Fallback: return stale data if available
            if cached_data:
                age = (now - cache_timestamp).total_seconds() if cache_timestamp else 999
                return cached_data, f"stale fallback ({int(age)}s old)"

            # Last resort: return minimal error data that won't break clients
            logger.warning("No cached data available, returning fallback")
            return {
                "train": "F/R TRAINS",
                "status": "Data temporarily unavailable",
                "status_type": "system_error",
                "active_trips": 0,
                "last_updated": now.isoformat(),
                "planned_work": [],
                "service_changes": [],
                "delays": []
            }, "error"

    except Exception as e:
        logger.error(f"Error in get_cached_data: {e}")
        # Return minimal safe data structure
        return {
            "train": "ERROR",
            "status": "Cache error",
            "status_type": "system_error",
            "active_trips": 0,
            "last_updated": datetime.now().isoformat(),
            "planned_work": [],
            "service_changes": [],
            "delays": []
        }, "cache_error"

def format_for_display(data):
    """Format data for terminal/display output (without emojis)"""
    lines = []
    lines.append(f"TRAIN: {data['train']}")
    lines.append("-" * 30)
    lines.append(f"Status: {data['status']}")

    if data['status_type'] == 'scheduled_maintenance':
        lines.append("   This is scheduled maintenance/construction work")

    lines.append(f"Active trips: {data['active_trips']}")

    if data.get('planned_work'):
        lines.append(f"Planned Work ({len(data['planned_work'])} items):")
        for item in data['planned_work']:
            lines.append(f"   • {item}")

    if data.get('service_changes'):
        lines.append(f"Service Changes ({len(data['service_changes'])} items):")
        for item in data['service_changes']:
            lines.append(f"   • {item}")

    if data.get('delays'):
        lines.append(f"Delays ({len(data['delays'])} items):")
        for item in data['delays']:
            lines.append(f"   • {item}")

    return "\n".join(lines)

@app.route('/health')
def health_check():
    """Health check with cache status"""
    with cache_lock:
        cache_age = None
        if cache_timestamp:
            cache_age = int((datetime.now() - cache_timestamp).total_seconds())

        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "cache_age_seconds": cache_age,
            "is_updating": is_updating,
            "has_cached_data": cached_data is not None
        })

@app.route('/transit/')
@app.route('/transit')
def get_transit():
    """Main endpoint - returns cached transit data"""
    try:
        data, data_source = get_cached_data()

        # Add cache info to response headers
        format_type = request.args.get('format', 'json')

        if format_type == 'text':
            response_text = format_for_display(data)
            response_text += f"\n\nData source: {data_source}"
            return response_text, 200, {
                'Content-Type': 'text/plain',
                'X-Data-Source': data_source
            }
        elif format_type == 'compact':
            # Compact JSON for MicroPython
            return app.response_class(
                response=json.dumps(data, separators=(',', ':')),
                status=200,
                mimetype='application/json',
                headers={'X-Data-Source': data_source}
            )
        else:
            # Standard JSON response
            response = jsonify(data)
            response.headers['X-Data-Source'] = data_source
            return response

    except Exception as e:
        logger.error(f"Error in get_transit: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/transit/lines')
def get_all_lines():
    """Get data for all train lines separately"""
    try:
        # Get cached data (never block)
        data, data_source = get_cached_data()

        # Extract raw data from cache
        raw_data = data.get('__raw_data__') if isinstance(data, dict) else None

        if not raw_data:
            # Fallback: return error data for each expected line
            return jsonify({
                "error": "Raw train line data not available",
                "data_source": data_source,
                "fallback_lines": {
                    "F": {
                        "train": "F TRAIN",
                        "line_id": "F",
                        "status": "Data temporarily unavailable",
                        "status_type": "system_error",
                        "active_trips": 0,
                        "last_updated": datetime.now().isoformat(),
                        "planned_work": [],
                        "service_changes": [],
                        "delays": []
                    },
                    "R": {
                        "train": "R TRAIN",
                        "line_id": "R",
                        "status": "Data temporarily unavailable",
                        "status_type": "system_error",
                        "active_trips": 0,
                        "last_updated": datetime.now().isoformat(),
                        "planned_work": [],
                        "service_changes": [],
                        "delays": []
                    }
                }
            }), 200

        # Process each line separately
        lines_data = {}
        for line_key, line_data in raw_data.items():
            if isinstance(line_data, dict):
                lines_data[line_key] = normalize_single_line_data(line_key, line_data)

        format_type = request.args.get('format', 'json')

        if format_type == 'compact':
            return app.response_class(
                response=json.dumps(lines_data, separators=(',', ':')),
                status=200,
                mimetype='application/json',
                headers={'X-Data-Source': data_source}
            )
        else:
            response = jsonify(lines_data)
            response.headers['X-Data-Source'] = data_source
            return response

    except Exception as e:
        logger.error(f"Error in get_all_lines: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/transit/line/<line_id>')
def get_single_line(line_id):
    """Get data for a specific train line (e.g., F or R)"""
    try:
        line_id = line_id.upper()  # Normalize to uppercase

        # Get cached data (never block)
        data, data_source = get_cached_data()

        # Extract raw data from cache
        raw_data = data.get('__raw_data__') if isinstance(data, dict) else None

        if not raw_data or line_id not in raw_data:
            # Return fallback data for the requested line
            fallback_data = {
                "train": f"{line_id} TRAIN",
                "line_id": line_id,
                "status": "Data temporarily unavailable",
                "status_type": "system_error",
                "active_trips": 0,
                "last_updated": datetime.now().isoformat(),
                "planned_work": [],
                "service_changes": [],
                "delays": [],
                "error": f"No cached data available for line {line_id}",
                "debug_info": {
                    "has_raw_data": raw_data is not None,
                    "available_lines": list(raw_data.keys()) if raw_data else [],
                    "data_source": data_source
                }
            }

            format_type = request.args.get('format', 'json')

            if format_type == 'compact':
                return app.response_class(
                    response=json.dumps(fallback_data, separators=(',', ':')),
                    status=200,
                    mimetype='application/json',
                    headers={'X-Data-Source': data_source}
                )
            else:
                response = jsonify(fallback_data)
                response.headers['X-Data-Source'] = data_source
                return response

        line_data = normalize_single_line_data(line_id, raw_data[line_id])

        format_type = request.args.get('format', 'json')

        if format_type == 'compact':
            return app.response_class(
                response=json.dumps(line_data, separators=(',', ':')),
                status=200,
                mimetype='application/json',
                headers={'X-Data-Source': data_source}
            )
        else:
            response = jsonify(line_data)
            response.headers['X-Data-Source'] = data_source
            return response

    except Exception as e:
        logger.error(f"Error in get_single_line: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/transit/status')
def get_status_only():
    """Lightweight endpoint for just status info"""
    try:
        data, data_source = get_cached_data()

        # Handle format parameter like main endpoint
        format_type = request.args.get('format', 'json')

        status_data = {
            "train": data.get("train", "Unknown"),
            "status": data.get("status", "Unknown"),
            "active_trips": data.get("active_trips", 0),
            "last_updated": data.get("last_updated", datetime.now().isoformat())
        }

        if format_type == 'compact':
            return app.response_class(
                response=json.dumps(status_data, separators=(',', ':')),
                status=200,
                mimetype='application/json',
                headers={'X-Data-Source': data_source}
            )
        else:
            response = jsonify(status_data)
            response.headers['X-Data-Source'] = data_source
            return response
    except Exception as e:
        logger.error(f"Error in get_status_only: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/transit/alerts')
def get_alerts_only():
    """Get only service disruptions and delays"""
    try:
        data, data_source = get_cached_data()
        alerts = []

        if data.get('delays'):
            alerts.extend([{"type": "delay", "message": msg} for msg in data['delays']])

        if data.get('service_changes'):
            alerts.extend([{"type": "service_change", "message": msg} for msg in data['service_changes']])

        alert_data = {
            "train": data.get("train", "Unknown"),
            "alert_count": len(alerts),
            "alerts": alerts
        }

        # Handle format parameter
        format_type = request.args.get('format', 'json')

        if format_type == 'compact':
            return app.response_class(
                response=json.dumps(alert_data, separators=(',', ':')),
                status=200,
                mimetype='application/json',
                headers={'X-Data-Source': data_source}
            )
        else:
            response = jsonify(alert_data)
            response.headers['X-Data-Source'] = data_source
            return response
    except Exception as e:
        logger.error(f"Error in get_alerts_only: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/cache/refresh')
def force_refresh():
    """Manually trigger cache refresh"""
    threading.Thread(target=update_cache, daemon=True).start()
    return jsonify({"message": "Cache refresh triggered"}), 200

@app.route('/cache/status')
def cache_status():
    """Get detailed cache status"""
    with cache_lock:
        cache_age = None
        if cache_timestamp:
            cache_age = int((datetime.now() - cache_timestamp).total_seconds())

        return jsonify({
            "has_data": cached_data is not None,
            "cache_age_seconds": cache_age,
            "is_updating": is_updating,
            "cache_duration": CACHE_DURATION,
            "update_interval": UPDATE_INTERVAL,
            "last_update": cache_timestamp.isoformat() if cache_timestamp else None
        })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "internal server error"}), 500

def start_background_updater():
    """Start the background cache updater thread"""
    global update_thread
    if update_thread is None or not update_thread.is_alive():
        update_thread = threading.Thread(target=background_updater, daemon=True)
        update_thread.start()
        logger.info("Background updater started")

# Custom request handler to suppress Flask request logs in console
class QuietWSGIRequestHandler(WSGIRequestHandler):
    def log_request(self, code='-', size='-'):
        # This suppresses the default console logging for requests
        pass

if __name__ == '__main__':
    print("TRANSIT SERVICE Starting...")
    print("Logging Configuration:")
    print("   Application logs: logs/transit_app.log")
    print("   Web request logs: logs/web_requests.log")
    print()
    print("Endpoints:")
    print("   GET /health           - Health check with cache status")
    print("   GET /transit          - Full transit data (cached)")
    print("   GET /transit?format=text - Formatted text output")
    print("   GET /transit?format=compact - Compact JSON")
    print("   GET /transit/status   - Status summary only")
    print("   GET /transit/alerts   - Alerts and delays only")
    print("   GET /transit/lines    - All train lines separately")
    print("   GET /transit/line/F   - F train data only")
    print("   GET /transit/line/R   - R train data only")
    print("   GET /cache/refresh    - Force cache refresh")
    print("   GET /cache/status     - Cache status info")
    print()
    print(f"Cache duration: {CACHE_DURATION}s, Update interval: {UPDATE_INTERVAL}s")
    print()

    # Initialize cache with fallback data first
    logger.info("Initializing cache with fallback data...")
    with cache_lock:
        cached_data = {
            "train": "INITIALIZING",
            "status": "Service starting up...",
            "status_type": "system_startup",
            "active_trips": 0,
            "last_updated": datetime.now().isoformat(),
            "planned_work": [],
            "service_changes": [],
            "delays": []
        }
        cache_timestamp = datetime.now()

    # Start background updater immediately
    start_background_updater()

    # Try to get initial real data (non-blocking)
    logger.info("Attempting to fetch initial real data...")
    threading.Thread(target=update_cache, daemon=True).start()

    logger.info("Service ready to accept requests!")
    print("Service ready to accept requests!")
    print()

    # Run Flask app with custom request handler to suppress console request logs
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # Disable debug to reduce console noise
        threaded=True,
        use_reloader=False,  # Disable reloader to prevent duplicate background threads
        request_handler=QuietWSGIRequestHandler  # Use custom handler to suppress request logs
    )

