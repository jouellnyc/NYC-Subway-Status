# hardware_manager.py - Hardware Control Module
# Handles button interrupts, LED control, and hardware initialization

import time
from machine import Pin
from config import PINS, TIMING

class HardwareManager:
    """Manages hardware components (buttons, LEDs, interrupts)"""
    
    def __init__(self, display_callback=None):
        """
        Initialize hardware manager
        
        Args:
            display_callback: Function to call for displaying messages
        """
        self.display_callback = display_callback if display_callback else self._dummy_display
        
        # Hardware components
        self.led = None
        self.button1 = None
        
        # Button state
        self.has_button = False
        self.button_interrupt_flag = False
        self.last_interrupt_time = 0
        
        # Initialize hardware
        self._init_led()
        self._init_button()
    
    def _dummy_display(self, text, color=None):
        """Fallback display function"""
        print(f"Hardware: {text}")
    
    def _init_led(self):
        """Initialize status LED"""
        try:
            self.led = Pin(PINS['led'], Pin.OUT)
            self.led.on()  # Start with LED on
            self.display_callback("LED initialized", "GREEN")
            return True
        except Exception as e:
            self.display_callback(f"LED init failed: {str(e)[:15]}", "YELLOW")
            return False
    
    def _init_button(self):
        """Initialize button with pull-up"""
        try:
            self.button1 = Pin(PINS['button1'], Pin.IN, Pin.PULL_UP)
            self.has_button = True
            self.display_callback("Button initialized", "GREEN")
            return True
        except Exception as e:
            self.display_callback(f"Button init failed: {str(e)[:15]}", "YELLOW")
            self.has_button = False
            return False
    
    def button_interrupt_handler(self, pin):
        """
        Button interrupt handler with debouncing
        
        Args:
            pin: Pin object that triggered the interrupt
        """
        try:
            current_time = time.ticks_ms()
            time_diff = time.ticks_diff(current_time, self.last_interrupt_time)
            
            # Debouncing - ignore if called within debounce period
            if time_diff > TIMING['interrupt_debounce_ms']:
                self.button_interrupt_flag = True
                self.last_interrupt_time = current_time
                
                # Optional: LED blink on button press
                if self.led:
                    self.led.off()
                    time.sleep_ms(50)
                    self.led.on()
            
        except Exception as e:
            # Ignore errors in interrupt handler to prevent crashes
            pass
    
    def setup_button_interrupt(self):
        """
        Setup button interrupt on falling edge
        
        Returns:
            bool: True if interrupt setup successful
        """
        if not self.has_button or not self.button1:
            return False
        
        try:
            # Set up interrupt on falling edge (button press)
            self.button1.irq(
                trigger=Pin.IRQ_FALLING, 
                handler=self.button_interrupt_handler
            )
            self.display_callback("Button interrupt enabled", "GREEN")
            return True
        except Exception as e:
            self.display_callback(f"Interrupt setup failed: {str(e)[:15]}", "RED")
            return False
    
    def check_interrupt(self):
        """
        Check if button interrupt occurred and handle it
        
        Returns:
            bool: True if interrupt occurred and was processed
        """
        if self.button_interrupt_flag:
            # Reset flag immediately to prevent multiple processing
            self.button_interrupt_flag = False
            self.display_callback("Button pressed", "CYAN")
            return True
        return False
    
    def disable_button_interrupt(self):
        """Disable button interrupt"""
        if self.has_button and self.button1:
            try:
                self.button1.irq(handler=None)
                self.display_callback("Button interrupt disabled", "YELLOW")
                return True
            except:
                return False
        return False
    
    def read_button_state(self):
        """
        Read current button state (for polling mode)
        
        Returns:
            bool: True if button is pressed (low = pressed with pull-up)
        """
        if self.has_button and self.button1:
            return not self.button1.value()  # Invert because of pull-up
        return False
    
    def led_on(self):
        """Turn LED on"""
        if self.led:
            self.led.on()
    
    def led_off(self):
        """Turn LED off"""
        if self.led:
            self.led.off()
    
    def led_toggle(self):
        """Toggle LED state"""
        if self.led:
            self.led.value(not self.led.value())
    
    def led_blink(self, on_ms=100, off_ms=100, count=1):
        """
        Blink LED specified number of times
        
        Args:
            on_ms: Time LED is on (milliseconds)
            off_ms: Time LED is off (milliseconds) 
            count: Number of blinks
        """
        if not self.led:
            return
        
        original_state = self.led.value()
        
        for _ in range(count):
            self.led.on()
            time.sleep_ms(on_ms)
            self.led.off()
            time.sleep_ms(off_ms)
        
        # Restore original state
        self.led.value(original_state)
    
    def heartbeat_blink(self):
        """Single heartbeat blink for status indication"""
        self.led_blink(on_ms=50, off_ms=50, count=1)
    
    def error_blink(self):
        """Error indication - rapid blinks"""
        self.led_blink(on_ms=100, off_ms=100, count=3)
    
    def success_blink(self):
        """Success indication - slow blinks"""
        self.led_blink(on_ms=200, off_ms=200, count=2)
    
    def get_hardware_status(self):
        """
        Get current hardware status
        
        Returns:
            dict: Hardware status information
        """
        return {
            'led_available': self.led is not None,
            'led_state': self.led.value() if self.led else None,
            'button_available': self.has_button,
            'button_state': self.read_button_state() if self.has_button else None,
            'interrupt_pending': self.button_interrupt_flag,
            'last_interrupt': self.last_interrupt_time
        }
    
    def test_hardware(self):
        """Test all hardware components"""
        self.display_callback("Testing hardware...", "CYAN")
        
        # Test LED
        if self.led:
            self.display_callback("Testing LED...", "WHITE")
            for i in range(3):
                self.led.on()
                time.sleep_ms(200)
                self.led.off()
                time.sleep_ms(200)
            self.led.on()  # Leave on
            self.display_callback("LED test complete", "GREEN")
        else:
            self.display_callback("LED not available", "YELLOW")
        
        # Test button
        if self.has_button:
            self.display_callback("Press button to test...", "WHITE")
            
            # Wait for button press with timeout
            start_time = time.ticks_ms()
            button_pressed = False
            
            while time.ticks_diff(time.ticks_ms(), start_time) < 5000:  # 5 second timeout
                if self.read_button_state():
                    button_pressed = True
                    break
                time.sleep_ms(100)
            
            if button_pressed:
                self.display_callback("Button test passed", "GREEN")
                self.success_blink()
            else:
                self.display_callback("Button test timeout", "YELLOW")
        else:
            self.display_callback("Button not available", "YELLOW")
        
        self.display_callback("Hardware test complete", "GREEN")
    
    def cleanup(self):
        """Clean up hardware resources"""
        # Disable interrupts
        self.disable_button_interrupt()
        
        # Turn off LED
        if self.led:
            self.led.off()
        
        self.display_callback("Hardware cleanup complete", "GREEN")

# Utility functions for easy import
def create_hardware_manager(display_callback=None):
    """Factory function to create hardware manager"""
    return HardwareManager(display_callback)

def quick_led_test():
    """Quick LED test without display callback"""
    hw = HardwareManager()
    if hw.led:
        hw.test_hardware()
        return True
    return False