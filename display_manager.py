# display_manager.py - TFT Display Management
# Handles all display operations with header protection and scrolling

import time
import gc
from config import DISPLAY_CONFIG, get_color_value, get_line_color_value

class DisplayManager:
    """Manages TFT display operations with scrolling and headers"""
    
    def __init__(self):
        self.tft = None
        self.has_display = False
        self.colors = {}
        
        # Display dimensions (set after init)
        self.width = 0
        self.height = 0
        self.font_height = 0
        self.font_width = 0
        self.max_chars = 0
        
        # Header management
        self.header_height = 0
        self.scroll_start_y = 0
        self.scroll_height = 0
        self.scroll_bottom_y = 0
        
        # Header state
        self.header_mode = False
        self.header_hold_time = 0
        self.header_text = ""
        self.header_color = None
        
        # Try to initialize display
        self._init_display()
    
    def _init_display(self):
        """Initialize TFT display if available"""
        try:
            import s3lcd
            import hardware.tft_config as tft_config
            import vga1_bold_16x32 as big
            
            # Initialize display
            self.tft = tft_config.config(tft_config.WIDE)
            self.tft.init()
            
            # Calculate dimensions
            self.height = self.tft.height()
            self.width = self.tft.width()
            self.font_height = big.HEIGHT
            self.font_width = big.WIDTH
            self.max_chars = self.width // self.font_width - 2
            
            # Define display areas
            self.header_height = self.font_height + 16
            self.scroll_start_y = self.header_height
            self.scroll_height = self.height - self.header_height
            self.scroll_bottom_y = self.height - self.font_height
            
            # Store font reference
            self.font = big
            
            # Define colors
            self.colors = {
                'WHITE': s3lcd.WHITE,
                'BLACK': s3lcd.BLACK,
                'RED': s3lcd.RED,
                'GREEN': s3lcd.GREEN,
                'YELLOW': s3lcd.YELLOW,
                'BLUE': s3lcd.BLUE,
                'ORANGE': 0xFD20,  # RGB565 format
                'CYAN': s3lcd.CYAN,
                'MAGENTA': s3lcd.MAGENTA
            }
            
            # Clear screen
            self.tft.fill(self.colors['BLACK'])
            self.tft.show()
            
            self.has_display = True
            print("Display initialized successfully")
            
        except ImportError as e:
            print(f"Display not available: {e}")
            self.has_display = False
            # Define dummy colors
            self.colors = {name: i for i, name in enumerate([
                'BLACK', 'WHITE', 'RED', 'GREEN', 'YELLOW', 
                'BLUE', 'ORANGE', 'CYAN', 'MAGENTA'
            ])}
    
    def get_color(self, color_name):
        """Get color value by name"""
        if isinstance(color_name, str):
            return self.colors.get(color_name, self.colors['WHITE'])
        return color_name  # Assume it's already a color value
    
    def get_line_color(self, line_id):
        """Get color for transit line"""
        return get_line_color_value(line_id, self.colors)
    
    def clear_screen(self):
        """Clear entire screen"""
        if not self.has_display:
            return
        self.tft.fill(self.colors['BLACK'])
        self.tft.show()
    
    def clear_scroll_area(self):
        """Clear only the scrolling area, preserve header"""
        if not self.has_display:
            return
        self.tft.fill_rect(0, self.scroll_start_y, self.width, self.scroll_height, self.colors['BLACK'])
    
    def show_header(self, text, color='BLUE', hold_time=7):
        """
        Show persistent header at top of screen
        
        Args:
            text: Header text to display
            color: Header text color
            hold_time: How long to hold header (seconds)
        """
        color_val = self.get_color(color)
        
        print(f"HEADER: {text}")
        
        if not self.has_display:
            return
        
        # Clear entire screen
        self.tft.fill(self.colors['BLACK'])
        
        # Set header state
        self.header_mode = True
        self.header_hold_time = time.ticks_ms() + (hold_time * 1000)
        self.header_text = text
        self.header_color = color_val
        
        # Draw header
        self.tft.text(self.font, self.header_text, 8, 8, self.header_color, self.colors['BLACK'])
        self.tft.show()
    
    def _redraw_header(self):
        """Redraw header in protected area"""
        if not self.has_display or not self.header_mode:
            return
        
        # Clear and redraw header area only
        self.tft.fill_rect(0, 0, self.width, self.header_height, self.colors['BLACK'])
        self.tft.text(self.font, self.header_text, 8, 8, self.header_color, self.colors['BLACK'])
    
    def _scroll_content_smooth(self):
        """Scroll content area smoothly while protecting header"""
        if not self.has_display:
            return
        
        try:
            # Smooth scroll pixel by pixel
            for step in range(self.font_height + 4):
                # Scroll entire screen
                self.tft.scroll(0, -1)
                
                # Immediately restore header
                if self.header_mode and self.header_text:
                    self._redraw_header()
                
                # Update display with small delay
                self.tft.show()
                time.sleep_ms(25)
            
            # Clear bottom area for new text
            self.tft.fill_rect(0, self.scroll_bottom_y, self.width, self.font_height, self.colors['BLACK'])
            
            # Final header restoration
            if self.header_mode:
                self._redraw_header()
                self.tft.show()
                
        except Exception as e:
            # Fallback: just clear bottom and redraw header
            self.tft.fill_rect(0, self.scroll_bottom_y, self.width, self.font_height, self.colors['BLACK'])
            if self.header_mode:
                self._redraw_header()
                self.tft.show()
    
    def _scroll_full_screen(self):
        """Normal full-screen scrolling (when no header)"""
        if not self.has_display:
            return
        
        try:
            # Smooth scroll by moving one pixel at a time
            for step in range(self.font_height):
                self.tft.scroll(0, -1)
                time.sleep_ms(DISPLAY_CONFIG['scroll_speed_ms'])
            
            # Clear bottom area for new text
            self.tft.fill_rect(0, self.height - self.font_height, self.width, self.font_height, self.colors['BLACK'])
            
        except:
            # Fallback: just clear bottom area
            self.tft.fill_rect(0, self.height - self.font_height, self.width, self.font_height, self.colors['BLACK'])
    
    def _display_single_line(self, text, color):
        """Display a single line with appropriate scrolling"""
        color_val = self.get_color(color)
        
        # Check if header mode is still active
        if self.header_mode and time.ticks_ms() < self.header_hold_time:
            # Header mode - scroll content area only
            if not self.has_display:
                time.sleep_ms(DISPLAY_CONFIG['text_pause_ms'])
                return
            
            # Scroll content area
            self._scroll_content_smooth()
            
            # Add text at bottom of scroll area
            self.tft.text(self.font, text, 8, self.scroll_bottom_y, color_val, self.colors['BLACK'])
            
            # Ensure header stays intact
            self._redraw_header()
            self.tft.show()
            time.sleep_ms(DISPLAY_CONFIG['text_pause_ms'])
            
        else:
            # Header hold period is over - normal scrolling
            if self.header_mode:
                self.header_mode = False
                # Clear any header separator if needed
                if self.has_display:
                    self.tft.fill_rect(0, self.header_height - 4, self.width, 4, self.colors['BLACK'])
            
            if not self.has_display:
                return
            
            # Normal full-screen scrolling
            self._scroll_full_screen()
            
            # Add new text at bottom
            self.tft.text(self.font, text, 8, self.height - self.font_height, color_val, self.colors['BLACK'])
            self.tft.show()
    
    def show_text(self, text, color='WHITE'):
        """
        Display text with word wrapping and scrolling
        
        Args:
            text: Text to display
            color: Text color (name or value)
        """
        print(text)
        
        if not self.has_display:
            return
        
        # Handle long lines with word wrapping  
        if len(text) > self.max_chars:
            words = text.split()
            line = ""
            
            for word in words:
                if len(line) + len(word) + 1 <= self.max_chars:
                    line = line + " " + word if line else word
                else:
                    if line:
                        self._display_single_line(line, color)
                    line = word
            
            if line:
                self._display_single_line(line, color)
        else:
            self._display_single_line(text, color)
    
    def show_multiline_text(self, lines, color='WHITE', delay_ms=None):
        """
        Show multiple lines of text with optional delay
        
        Args:
            lines: List of text lines
            color: Text color
            delay_ms: Delay between lines (uses config default if None)
        """
        if delay_ms is None:
            delay_ms = DISPLAY_CONFIG['text_pause_ms']
        
        for line in lines:
            self.show_text(line, color)
            time.sleep_ms(delay_ms)
    
    def extend_header_mode(self, additional_seconds=30):
        """Extend header hold time"""
        if self.header_mode:
            self.header_hold_time = time.ticks_ms() + (additional_seconds * 1000)
    
    def end_header_mode(self):
        """Force end header mode"""
        self.header_mode = False
    
    def is_header_active(self):
        """Check if header mode is currently active"""
        if not self.header_mode:
            return False
        return time.ticks_ms() < self.header_hold_time
    
    def get_display_info(self):
        """Get display information for debugging"""
        return {
            'has_display': self.has_display,
            'width': self.width,
            'height': self.height,
            'font_height': self.font_height,
            'max_chars': self.max_chars,
            'header_active': self.is_header_active(),
            'header_text': self.header_text if self.header_mode else None
        }
    
    def cleanup(self):
        """Clean up display resources"""
        if self.has_display:
            try:
                self.tft.fill(self.colors['BLACK'])
                self.tft.show()
            except:
                pass
        gc.collect()

# Utility functions
def create_display_manager():
    """Factory function to create display manager"""
    return DisplayManager()

def get_display_callback(display_manager):
    """Get a callback function for other modules to use"""
    def display_callback(text, color='WHITE'):
        display_manager.show_text(text, color)
    return display_callback