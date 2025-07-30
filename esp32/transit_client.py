# transit_client.py - Transit API Client Module
# Handles all communication with the transit service API

import urequests
import ujson
import time
import gc
from config import SERVICE_URL, MEMORY_CONFIG

class TransitClient:
    """Handles transit API communication and data processing"""
    
    def __init__(self, display_callback=None, quiet_mode=False):
        """
        Initialize transit client
        
        Args:
            display_callback: Function to call for displaying messages
            quiet_mode: If True, suppress status messages during data fetching
        """
        self.service_url = SERVICE_URL
        self.display_callback = display_callback if display_callback else self._dummy_display
        self.quiet_mode = quiet_mode
        self.last_request_time = 0
        self.request_count = 0
        
        # Cache for reducing API calls
        self.cache = {}
        self.cache_timeout = 30000  # 30 seconds in milliseconds
    
    def _dummy_display(self, text, color=None):
        """Fallback display function"""
        print(f"Transit: {text}")
    
    def _show_status(self, text, color=None):
        """Show status message only if not in quiet mode"""
        if not self.quiet_mode:
            self.display_callback(text, color)
    
    def set_quiet_mode(self, quiet=True):
        """Enable or disable quiet mode"""
        self.quiet_mode = quiet
    
    def _make_request(self, url, timeout=30):
        """
        Make HTTP request with error handling
        
        Args:
            url: URL to request
            timeout: Request timeout in seconds
            
        Returns:
            dict or None: JSON response data or None if failed
        """
        self.request_count += 1
        self.last_request_time = time.ticks_ms()
        
        try:
            response = urequests.get(url, timeout=timeout)
            
            if response.status_code == 200:
                data = ujson.loads(response.text)
                response.close()
                
                # Force garbage collection after successful request
                gc.collect()
                return data
            else:
                self._show_status(f"HTTP {response.status_code}", "YELLOW")
                response.close()
                return None
                
        except OSError as e:
            # Network errors
            self._show_status("Network error", "RED")
            return None
        except ValueError as e:
            # JSON parsing errors
            self._show_status("JSON parse error", "RED")
            return None
        except Exception as e:
            # Other errors
            error_msg = f"Request error: {str(e)[:20]}"
            self._show_status(error_msg, "RED")
            return None
    
    def _get_cache_key(self, endpoint):
        """Generate cache key for endpoint"""
        return f"cache_{endpoint.replace('/', '_')}"
    
    def _is_cache_valid(self, cache_key):
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key].get('timestamp', 0)
        current_time = time.ticks_ms()
        
        return time.ticks_diff(current_time, cached_time) < self.cache_timeout
    
    def _cache_data(self, cache_key, data):
        """Cache data with timestamp"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.ticks_ms()
        }
        
        # Limit cache size to prevent memory issues
        if len(self.cache) > 5:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
    
    def _get_cached_data(self, cache_key):
        """Get data from cache"""
        if cache_key in self.cache:
            return self.cache[cache_key]['data']
        return None
    
    def health_check(self):
        """
        Check if transit service is available
        
        Returns:
            bool: True if service is healthy
        """
        url = f"{self.service_url}/health"
        
        try:
            response = urequests.get(url, timeout=5)
            is_healthy = response.status_code == 200
            response.close()
            
            if is_healthy:
                self._show_status("Service healthy", "GREEN")
            else:
                self._show_status("Service unhealthy", "RED")
            
            return is_healthy
            
        except Exception as e:
            self._show_status("Health check failed", "RED")
            return False
    
    def fetch_line_data(self, line_id, quiet=None):
        """
        Fetch data for specific transit line
        
        Args:
            line_id: Transit line identifier (e.g., 'F', 'R')
            quiet: Override instance quiet_mode for this call
            
        Returns:
            dict or None: Line data or None if failed
        """
        endpoint = f"transit/line/{line_id}"
        cache_key = self._get_cache_key(endpoint)
        
        # Determine if we should show status messages
        show_messages = not (quiet if quiet is not None else self.quiet_mode)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            if show_messages:
                self.display_callback(f"Using cached {line_id} data", "CYAN")
            return self._get_cached_data(cache_key)
        
        # Make API request
        url = f"{self.service_url}/{endpoint}"
        if show_messages:
            self.display_callback(f"Fetching {line_id} data...", "CYAN")
        
        data = self._make_request(url)
        
        if data:
            # Cache successful response
            self._cache_data(cache_key, data)
            if show_messages:
                self.display_callback(f"{line_id} data fetched", "GREEN")
        else:
            if show_messages:
                self.display_callback(f"{line_id} fetch failed", "RED")
                
            # Try to return stale cache data as fallback
            if cache_key in self.cache:
                if show_messages:
                    self.display_callback("Using stale cache", "YELLOW")
                return self._get_cached_data(cache_key)
        
        return data
    
    # ... rest of the methods remain the same ...
    def fetch_general_status(self, format="compact"):
        """
        Fetch general transit status
        
        Args:
            format: Response format ('compact' or 'full')
            
        Returns:
            dict or None: Status data or None if failed
        """
        endpoint = f"transit/status?format={format}"
        cache_key = self._get_cache_key(endpoint)
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return self._get_cached_data(cache_key)
        
        # Make request
        url = f"{self.service_url}/{endpoint}"
        data = self._make_request(url)
        
        if data:
            self._cache_data(cache_key, data)
        
        return data
    
    def fetch_alerts(self, line_id=None):
        """
        Fetch alerts for specific line or all lines
        
        Args:
            line_id: Specific line ID or None for all alerts
            
        Returns:
            dict or None: Alert data or None if failed
        """
        if line_id:
            endpoint = f"transit/alerts/{line_id}"
        else:
            endpoint = "transit/alerts"
        
        cache_key = self._get_cache_key(endpoint)
        
        if self._is_cache_valid(cache_key):
            return self._get_cached_data(cache_key)
        
        url = f"{self.service_url}/{endpoint}"
        data = self._make_request(url)
        
        if data:
            self._cache_data(cache_key, data)
        
        return data
    
    def format_timestamp(self, timestamp_str):
        """
        Format timestamp for display
        
        Args:
            timestamp_str: ISO timestamp string
            
        Returns:
            str: Formatted time string
        """
        if not timestamp_str:
            return "Time unknown"
        
        try:
            # Parse ISO timestamp: "2024-01-15T14:30:25"
            date_part, time_part = timestamp_str.split('T')
            year, month, day = date_part.split('-')
            hour, minute, _ = time_part.split(':')
            
            return f"{month}/{day} - {hour}:{minute}"
        except:
            return "Time format error"
    
    def display_planned_work(self, planned_work_list, display_manager):
        """
        Display planned work with proper formatting
        
        Args:
            planned_work_list: List of planned work text
            display_manager: Display manager instance for showing text
        """
        for work_text in planned_work_list:
            # Clean up text
            clean_text = work_text.replace('\n', ' ').replace('  ', ' ')
            
            # Split into sentences for better display
            sentences = self._split_into_sentences(clean_text)
            
            # Display each sentence
            for sentence in sentences:
                if sentence.strip():
                    # Truncate if too long
                    if len(sentence) > MEMORY_CONFIG['max_text_length']:
                        sentence = sentence[:MEMORY_CONFIG['max_text_length']] + "..."
                    
                    display_manager.show_text(sentence.strip(), "YELLOW")
                    time.sleep_ms(1200)
    
    def _split_into_sentences(self, text):
        """
        Split text into sentences for better display
        
        Args:
            text: Input text
            
        Returns:
            list: List of sentences
        """
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if char in '.!?' and len(current) > 50:
                sentences.append(current.strip())
                current = ""
        
        if current.strip():
            sentences.append(current.strip())
        
        return sentences
    
    def process_service_status(self, data):
        """
        Process and format service status data
        
        Args:
            data: Raw service data from API
            
        Returns:
            dict: Processed status information
        """
        if not data:
            return None
        
        processed = {
            'train': data.get('train', 'Unknown'),
            'status': data.get('status', 'Unknown'),
            'last_updated': self.format_timestamp(data.get('last_updated', '')),
            'active_trips': data.get('active_trips', 0),
            'active_alerts': data.get('active_alerts', 0),
            'has_issues': data.get('status', 'Good Service') != 'Good Service'
        }
        
        # Process delays
        delays = data.get('delays', [])
        processed['delay_count'] = len(delays)
        processed['delays'] = delays[:3]  # Limit to first 3 for memory
        
        # Process service changes
        service_changes = data.get('service_changes', [])
        processed['service_change_count'] = len(service_changes)
        processed['service_changes'] = service_changes[:3]
        
        # Process planned work
        planned_work = data.get('planned_work', [])
        processed['planned_work_count'] = len(planned_work)
        processed['planned_work'] = planned_work[:2]  # Limit for memory
        
        return processed
    
    def get_client_stats(self):
        """
        Get client statistics for debugging
        
        Returns:
            dict: Client statistics
        """
        return {
            'request_count': self.request_count,
            'last_request': self.last_request_time,
            'cache_entries': len(self.cache),
            'service_url': self.service_url,
            'cache_timeout_ms': self.cache_timeout,
            'quiet_mode': self.quiet_mode
        }
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        self._show_status("Cache cleared", "GREEN")
        gc.collect()
    
    def test_connection(self):
        """
        Test connection to transit service
        
        Returns:
            bool: True if connection test passed
        """
        self._show_status("Testing transit connection...", "CYAN")
        
        # Test health endpoint
        if not self.health_check():
            return False
        
        # Test data fetch
        test_data = self.fetch_line_data('F')
        if test_data:
            self._show_status("Transit test passed", "GREEN")
            return True
        else:
            self._show_status("Transit test failed", "RED")
            return False
    
    def cleanup(self):
        """Clean up client resources"""
        self.clear_cache()
        self._show_status("Transit client cleanup complete", "GREEN")

# Utility functions for easy import
def create_transit_client(display_callback=None, quiet_mode=False):
    """Factory function to create transit client"""
    return TransitClient(display_callback, quiet_mode)

def quick_health_check():
    """Quick health check without display callback"""
    client = TransitClient()
    return client.health_check()

def quick_line_test(line_id='F'):
    """Quick test of line data fetch"""
    client = TransitClient()
    data = client.fetch_line_data(line_id)
    if data:
        print(f"Line {line_id} status: {data.get('status', 'Unknown')}")
        return True
    return False