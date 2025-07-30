# config.py - All configuration constants
# Centralized configuration for MicroPython Transit Monitor

# Service Configuration
SERVICE_URL = "http://192.168.0.23:5000"

# PPP Configuration
PPP_CONFIG = {
    'uart_id': 1,
    'baudrate': 9600,
    'tx_pin': 44,
    'rx_pin': 43,
    'timeout': 30,
    'reconnect_interval': 10
}

# Hardware Pin Configuration
PINS = {
    'led': 2,
    'button1': 0
}

# Display Configuration
DISPLAY_CONFIG = {
    'max_chars_per_line': None,  # Will be calculated
    'header_height': None,       # Will be calculated
    'font_height': None,         # Will be calculated
    'scroll_speed_ms': 15,
    'text_pause_ms': 800,
    'header_hold_time': 7        # seconds
}

# Transit Lines
TRANSIT_LINES = ['F', 'R']

# Subway Line Colors (MTA Official Colors)
SUBWAY_LINE_COLORS = {
    # IND Sixth Avenue Line (Orange)
    'F': 'ORANGE',
    'M': 'ORANGE',
    
    # BMT Broadway Line (Yellow)  
    'N': 'YELLOW',
    'Q': 'YELLOW',
    'R': 'YELLOW',
    'W': 'YELLOW',
    
    # IRT Lexington Avenue Line (Green)
    '4': 'GREEN',
    '5': 'GREEN',
    '6': 'GREEN',
    
    # IND Eighth Avenue Line (Blue)
    'A': 'BLUE',
    'C': 'BLUE',
    'E': 'BLUE',
    
    # BMT Canarsie Line (White)
    'L': 'WHITE',
    
    # Default
    'DEFAULT': 'WHITE'
}

# Memory Management
MEMORY_CONFIG = {
    'low_memory_threshold': 10000,
    'gc_interval': 10,           # Run GC every N cycles
    'max_text_length': 200       # Truncate long texts
}

# Timing Configuration
TIMING = {
    'line_display_duration': 10,  # seconds per line
    'startup_delay': 2,           # seconds
    'interrupt_debounce_ms': 500,
    'connection_retry_delay': 5   # seconds
}

# Error Messages
ERROR_MESSAGES = {
    'no_display': "Display not available",
    'ppp_init_failed': "PPP init failed",
    'ppp_connect_failed': "PPP connection failed", 
    'service_down': "Service unavailable",
    'no_data': "No data available",
    'low_memory': "Low memory warning",
    'button_failed': "Button setup failed"
}

# Success Messages  
SUCCESS_MESSAGES = {
    'ppp_connected': "PPP Connected!",
    'service_ok': "Service OK",
    'startup_complete': "System Ready",
    'button_enabled': "Button enabled"
}

# Color Mapping Function
def get_color_value(color_name, color_constants):
    """Map color names to actual color values"""
    color_map = {
        'WHITE': color_constants.get('WHITE', 1),
        'BLACK': color_constants.get('BLACK', 0), 
        'RED': color_constants.get('RED', 2),
        'GREEN': color_constants.get('GREEN', 3),
        'YELLOW': color_constants.get('YELLOW', 4),
        'BLUE': color_constants.get('BLUE', 5),
        'ORANGE': color_constants.get('ORANGE', 6),
        'CYAN': color_constants.get('CYAN', 7),
        'MAGENTA': color_constants.get('MAGENTA', 8)
    }
    return color_map.get(color_name, color_map['WHITE'])

def get_line_color_value(line_id, color_constants):
    """Get color value for specific transit line"""
    color_name = SUBWAY_LINE_COLORS.get(line_id, SUBWAY_LINE_COLORS['DEFAULT'])
    return get_color_value(color_name, color_constants)