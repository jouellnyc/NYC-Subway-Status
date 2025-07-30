# ppp_manager.py - PPP Connectivity Management
# Handles all PPP connection logic with display feedback

import time
import network
import machine
import gc
from config import PPP_CONFIG, ERROR_MESSAGES, SUCCESS_MESSAGES

class PPPManager:
    """Manages PPP connectivity with visual feedback"""
    
    def __init__(self, display_callback=None):
        """
        Initialize PPP Manager
        
        Args:
            display_callback: Function to call for displaying messages
                            Should accept (text, color) parameters
        """
        self.uart_id = PPP_CONFIG['uart_id']
        self.baudrate = PPP_CONFIG['baudrate'] 
        self.tx = PPP_CONFIG['tx_pin']
        self.rx = PPP_CONFIG['rx_pin']
        self.timeout = PPP_CONFIG['timeout']
        
        self.ppp = None
        self.uart = None
        self.connected = False
        self.last_status_check = 0
        self.connection_attempts = 0
        
        # Display callback for showing messages
        self.show_message = display_callback if display_callback else self._dummy_display
        
    def _dummy_display(self, text, color=None):
        """Fallback display function if no callback provided"""
        print(f"PPP: {text}")
    
    def init_hardware(self):
        """Initialize UART and PPP interface"""
        try:
            self.uart = machine.UART(
                self.uart_id, 
                baudrate=self.baudrate,
                tx=self.tx, 
                rx=self.rx
            )
            
            self.ppp = network.PPP(self.uart)
            self.ppp.active(True)
            
            self.show_message("PPP interface initialized", "GREEN")
            return True
            
        except Exception as e:
            error_msg = f"{ERROR_MESSAGES['ppp_init_failed']}: {str(e)[:20]}"
            self.show_message(error_msg, "RED")
            return False
    
    def connect(self, timeout=None, show_progress=True):
        """
        Connect PPP with optional visual feedback
        
        Args:
            timeout: Connection timeout in seconds (uses config default if None)
            show_progress: Whether to show connection progress
            
        Returns:
            bool: True if connected successfully
        """
        if timeout is None:
            timeout = self.timeout
            
        # Initialize hardware if not already done
        if not self.ppp and not self.init_hardware():
            return False
        
        self.connection_attempts += 1
        
        if show_progress:
            self.show_message("Connecting PPP...", "CYAN")
        
        try:
            self.ppp.connect()
            
            # Connection progress with visual feedback
            for i in range(timeout):
                if self.ppp.isconnected():
                    self.connected = True
                    
                    if show_progress:
                        self.show_message(SUCCESS_MESSAGES['ppp_connected'], "GREEN")
                        
                        # Show IP address
                        try:
                            config = self.ppp.ifconfig()
                            ip = config[0] if config and len(config) > 0 else "Unknown"
                            self.show_message(f"IP: {ip}", "GREEN")
                        except:
                            self.show_message("IP: Unable to retrieve", "YELLOW")
                    
                    # Force garbage collection after successful connection
                    gc.collect()
                    return True
                
                # Show progress animation
                if show_progress and i % 3 == 0:
                    dots = "." * ((i // 3) % 4)
                    self.show_message(f"Connecting{dots}", "CYAN")
                
                time.sleep(1)
            
            # Connection timeout
            self.connected = False
            if show_progress:
                self.show_message(ERROR_MESSAGES['ppp_connect_failed'], "RED")
            return False
            
        except Exception as e:
            self.connected = False
            error_msg = f"PPP error: {str(e)[:25]}"
            if show_progress:
                self.show_message(error_msg, "RED")
            return False
    
    def disconnect(self, show_message=True):
        """Disconnect PPP connection"""
        if self.ppp:
            try:
                self.ppp.disconnect()
                self.connected = False
                if show_message:
                    self.show_message("PPP Disconnected", "YELLOW")
            except Exception as e:
                if show_message:
                    self.show_message(f"Disconnect error: {str(e)[:15]}", "RED")
    
    def is_connected(self):
        """
        Check if PPP is currently connected
        
        Returns:
            bool: True if connected
        """
        if not self.ppp:
            return False
            
        try:
            connected = self.ppp.isconnected()
            self.connected = connected
            return connected
        except:
            self.connected = False
            return False
    
    def get_status(self, detailed=False):
        """
        Get current PPP status
        
        Args:
            detailed: If True, return dict with detailed info
            
        Returns:
            str or dict: Status information
        """
        if not self.ppp:
            return "PPP: Not initialized" if not detailed else {
                'status': 'not_initialized',
                'connected': False,
                'ip': None,
                'attempts': self.connection_attempts
            }
        
        connected = self.is_connected()
        
        if detailed:
            status_info = {
                'status': 'connected' if connected else 'disconnected',
                'connected': connected,
                'ip': None,
                'attempts': self.connection_attempts
            }
            
            if connected:
                try:
                    config = self.ppp.ifconfig()
                    status_info['ip'] = config[0] if config and len(config) > 0 else "Unknown"
                except:
                    status_info['ip'] = "Unknown"
            
            return status_info
        
        else:
            if connected:
                try:
                    config = self.ppp.ifconfig()
                    ip = config[0] if config and len(config) > 0 else "Unknown"
                    return f"PPP: Connected ({ip})"
                except:
                    return "PPP: Connected (IP unknown)"
            else:
                return "PPP: Disconnected"
    
    def auto_reconnect(self, max_attempts=3):
        """
        Attempt automatic reconnection
        
        Args:
            max_attempts: Maximum reconnection attempts
            
        Returns:
            bool: True if reconnection successful
        """
        if self.is_connected():
            return True
        
        self.show_message("Auto-reconnecting PPP...", "YELLOW")
        
        for attempt in range(max_attempts):
            self.show_message(f"Attempt {attempt + 1}/{max_attempts}", "CYAN")
            
            if self.connect(timeout=15, show_progress=False):
                self.show_message("Reconnection successful", "GREEN")
                return True
            
            if attempt < max_attempts - 1:
                time.sleep(PPP_CONFIG['reconnect_interval'])
        
        self.show_message("Reconnection failed", "RED")
        return False
    
    def get_connection_info(self):
        """Get detailed connection information for debugging"""
        if not self.ppp:
            return "PPP not initialized"
        
        try:
            if self.is_connected():
                config = self.ppp.ifconfig()
                return {
                    'connected': True,
                    'ip': config[0] if config else "Unknown",
                    'netmask': config[1] if len(config) > 1 else "Unknown", 
                    'gateway': config[2] if len(config) > 2 else "Unknown",
                    'dns': config[3] if len(config) > 3 else "Unknown",
                    'attempts': self.connection_attempts
                }
            else:
                return {
                    'connected': False,
                    'attempts': self.connection_attempts
                }
        except Exception as e:
            return f"Error getting info: {str(e)}"
    
    def cleanup(self):
        """Clean up resources"""
        self.disconnect(show_message=False)
        if self.ppp:
            try:
                self.ppp.active(False)
            except:
                pass
        self.ppp = None
        self.uart = None
        gc.collect()

# Utility functions for easy import
def create_ppp_manager(display_callback=None):
    """Factory function to create a PPP manager"""
    return PPPManager(display_callback)

def quick_connect(display_callback=None, timeout=30):
    """Quick PPP connection for simple use cases"""
    ppp = PPPManager(display_callback)
    return ppp.connect(timeout=timeout), ppp