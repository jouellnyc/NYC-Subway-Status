# utils.py - Utility Functions Module
# Common utility functions used across the application

import gc
import time
from config import MEMORY_CONFIG

def memory_info():
    """
    Get current memory information
    
    Returns:
        dict: Memory information
    """
    try:
        gc.collect()  # Force garbage collection first
        free = gc.mem_free()
        allocated = gc.mem_alloc()
        total = free + allocated
        
        return {
            'free': free,
            'allocated': allocated,
            'total': total,
            'free_percent': (free / total * 100) if total > 0 else 0,
            'is_low': free < MEMORY_CONFIG['low_memory_threshold']
        }
    except Exception as e:
        return {
            'error': str(e),
            'free': None,
            'allocated': None,
            'total': None,
            'free_percent': None,
            'is_low': True
        }

def format_memory(bytes_value):
    """
    Format bytes value for human-readable display
    
    Args:
        bytes_value: Number of bytes
        
    Returns:
        str: Formatted string (e.g., "15.2KB", "1.5MB")
    """
    if bytes_value is None:
        return "Unknown"
    
    if bytes_value < 1024:
        return f"{bytes_value}B"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.1f}KB"
    else:
        return f"{bytes_value / (1024 * 1024):.1f}MB"

def check_low_memory(display_callback=None):
    """
    Check if memory is low and optionally display warning
    
    Args:
        display_callback: Optional callback to display warning
        
    Returns:
        bool: True if memory is low
    """
    mem_info = memory_info()
    
    if mem_info.get('is_low', True):
        message = f"Low memory: {format_memory(mem_info.get('free'))}"
        
        if display_callback:
            display_callback(message, "YELLOW")
        else:
            print(message)
        
        # Force garbage collection
        gc.collect()
        return True
    
    return False

def truncate_text(text, max_length, suffix="..."):
    """
    Truncate text to maximum length with optional suffix
    
    Args:
        text: Input text
        max_length: Maximum allowed length
        suffix: Suffix to add when truncating
        
    Returns:
        str: Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    truncate_length = max_length - len(suffix)
    if truncate_length <= 0:
        return suffix[:max_length]
    
    return text[:truncate_length] + suffix

def split_long_text(text, max_chars_per_line):
    """
    Split long text into multiple lines with word wrapping
    
    Args:
        text: Input text
        max_chars_per_line: Maximum characters per line
        
    Returns:
        list: List of text lines
    """
    if not text:
        return []
    
    if len(text) <= max_chars_per_line:
        return [text]
    
    lines = []
    words = text.split()
    current_line = ""
    
    for word in words:
        # Check if adding this word would exceed the limit
        test_line = current_line + " " + word if current_line else word
        
        if len(test_line) <= max_chars_per_line:
            current_line = test_line
        else:
            # Current line is complete
            if current_line:
                lines.append(current_line)
            
            # Start new line with current word
            current_line = word
            
            # Handle case where single word is longer than max_chars
            if len(current_line) > max_chars_per_line:
                # Split the word itself
                while len(current_line) > max_chars_per_line:
                    lines.append(current_line[:max_chars_per_line])
                    current_line = current_line[max_chars_per_line:]
    
    # Add the last line if it has content
    if current_line:
        lines.append(current_line)
    
    return lines

def format_uptime(start_time_ms):
    """
    Format uptime from start time
    
    Args:
        start_time_ms: Start time in ticks_ms()
        
    Returns:
        str: Formatted uptime string
    """
    try:
        current_time = time.ticks_ms()
        uptime_ms = time.ticks_diff(current_time, start_time_ms)
        
        # Convert to seconds
        uptime_seconds = uptime_ms // 1000
        
        # Calculate components
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    except:
        return "Unknown"

def safe_int(value, default=0):
    """
    Safely convert value to integer
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        int: Converted integer or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_str(value, default="Unknown"):
    """
    Safely convert value to string
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        str: Converted string or default
    """
    try:
        if value is None:
            return default
        return str(value)
    except:
        return default

def create_status_summary(components):
    """
    Create a status summary from component statuses
    
    Args:
        components: Dict of component_name: is_healthy pairs
        
    Returns:
        dict: Status summary
    """
    total = len(components)
    healthy = sum(1 for status in components.values() if status)
    
    return {
        'total_components': total,
        'healthy_components': healthy,
        'failed_components': total - healthy,
        'overall_healthy': healthy == total,
        'health_percentage': (healthy / total * 100) if total > 0 else 0,
        'component_details': components
    }

def debounce_function(func, delay_ms=500):
    """
    Create a debounced version of a function
    
    Args:
        func: Function to debounce
        delay_ms: Debounce delay in milliseconds
        
    Returns:
        function: Debounced function
    """
    last_call_time = [0]  # Use list to allow modification in closure
    
    def debounced_func(*args, **kwargs):
        current_time = time.ticks_ms()
        
        if time.ticks_diff(current_time, last_call_time[0]) >= delay_ms:
            last_call_time[0] = current_time
            return func(*args, **kwargs)
        
        return None  # Call was debounced
    
    return debounced_func

def retry_operation(func, max_attempts=3, delay_ms=1000, exponential_backoff=False):
    """
    Retry an operation with configurable attempts and delay
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        delay_ms: Delay between attempts in milliseconds
        exponential_backoff: Whether to use exponential backoff
        
    Returns:
        tuple: (success: bool, result: any, attempts: int)
    """
    for attempt in range(max_attempts):
        try:
            result = func()
            return True, result, attempt + 1
        
        except Exception as e:
            if attempt == max_attempts - 1:  # Last attempt
                return False, str(e), attempt + 1
            
            # Calculate delay
            if exponential_backoff:
                current_delay = delay_ms * (2 ** attempt)
            else:
                current_delay = delay_ms
            
            time.sleep_ms(current_delay)
    
    return False, "Max attempts exceeded", max_attempts

def clean_text_for_display(text, max_length=None):
    """
    Clean text for display by removing unwanted characters and formatting
    
    Args:
        text: Input text
        max_length: Optional maximum length
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Replace multiple whitespace with single space
    cleaned = ' '.join(text.split())
    
    # Remove or replace problematic characters
    cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # Truncate if needed
    if max_length and len(cleaned) > max_length:
        cleaned = truncate_text(cleaned, max_length)
    
    return cleaned

def get_system_info():
    """
    Get system information for debugging
    
    Returns:
        dict: System information
    """
    try:
        import sys
        import os
        
        info = {
            'platform': sys.platform,
            'version': sys.version,
            'implementation': sys.implementation.name if hasattr(sys, 'implementation') else 'unknown'
        }
        
        # Add memory info
        info.update(memory_info())
        
        return info
        
    except Exception as e:
        return {'error': str(e)}

# Convenience functions for common operations
def print_memory_status():
    """Print current memory status to console"""
    mem_info = memory_info()
    if 'error' in mem_info:
        print(f"Memory check failed: {mem_info['error']}")
    else:
        print(f"Memory: {format_memory(mem_info['free'])} free / {format_memory(mem_info['total'])} total ({mem_info['free_percent']:.1f}% free)")

def force_cleanup():
    """Force garbage collection and return memory info"""
    gc.collect()
    return memory_info()