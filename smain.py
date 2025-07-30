# main.py - Modular MicroPython Transit Monitor
# Main application orchestrating all modules

import gc
import time
from config import TRANSIT_LINES, TIMING, MEMORY_CONFIG

# Core modules - import immediately
from display_manager import DisplayManager, get_display_callback
from ppp_manager import PPPManager

# Global managers
display = None
ppp = None
hardware = None
transit = None

# Application state
current_line_index = 0
running = True
cycle_count = 0

def init_display():
    """Initialize display manager"""
    global display
    try:
        display = DisplayManager()
        if display.has_display:
            display.show_text("MTA R/F MONITOR", "GREEN")
            display.show_text("Modular Version", "WHITE")
            return True
        else:
            print("Display not available, using console output")
            return False
    except Exception as e:
        print(f"Display init failed: {e}")
        return False

def init_ppp():
    """Initialize PPP manager with display callback"""
    global ppp, display
    try:
        # Get display callback
        display_callback = get_display_callback(display) if display else None
        
        # Create PPP manager
        ppp = PPPManager(display_callback)
        
        # Attempt connection
        if ppp.connect():
            return True
        else:
            if display:
                display.show_text("PPP Failed - Continuing", "RED")
            return False
            
    except Exception as e:
        error_msg = f"PPP init error: {str(e)[:20]}"
        if display:
            display.show_text(error_msg, "RED")
        else:
            print(error_msg)
        return False

def init_hardware():
    """Initialize hardware manager (lazy loaded)"""
    global hardware
    try:
        # Lazy import to save memory
        import hardware_manager
        hardware = hardware_manager.HardwareManager(
            display_callback=get_display_callback(display) if display else None
        )
        
        if hardware.setup_button_interrupt():
            if display:
                display.show_text("Button enabled", "GREEN")
        elif hardware.has_button:
            if display:
                display.show_text("Button setup failed", "YELLOW")
                
        return True
        
    except ImportError:
        if display:
            display.show_text("Hardware module missing", "YELLOW")
        return False
    except Exception as e:
        error_msg = f"Hardware init error: {str(e)[:15]}"
        if display:
            display.show_text(error_msg, "RED")
        return False


def init_transit_client():
    """Initialize transit client (lazy loaded)"""
    global transit
    try:
        # Lazy import
        import transit_client
        transit = transit_client.TransitClient(
            display_callback=get_display_callback(display) if display else None,
            quiet_mode=True  # Enable quiet mode to prevent status message interruptions
        )
        
        # Test service connectivity (this will still show messages since it's initialization)
        if transit.health_check():
            if display:
                display.show_text("Service OK", "GREEN")
            return True
        else:
            if display:
                display.show_text("Service down", "RED")
            return False
            
    except ImportError:
        if display:
            display.show_text("Transit module missing", "RED")
        return False
    except Exception as e:
        error_msg = f"Transit init error: {str(e)[:15]}"
        if display:
            display.show_text(error_msg, "RED")
        return False
    

def check_button_interrupt():
    """Check for button press and handle line switching"""
    global current_line_index, hardware
    
    if not hardware:
        return False
        
    if hardware.check_interrupt():
        # Switch to next line
        current_line_index = (current_line_index + 1) % len(TRANSIT_LINES)
        
        if display:
            display.show_text(f"Switching to {TRANSIT_LINES[current_line_index]} line...", "GREEN")
            time.sleep_ms(300)
            display.clear_screen()
        
        return True
    return False

def show_line_status(line_id):
    """Display status for specific transit line"""
    if not transit or not display:
        return
    
    # Get line data
    data = transit.fetch_line_data(line_id)
    
    if not data:
        line_color = display.get_line_color(line_id)
        display.show_header(f"=== {line_id} TRAIN ===", line_color)
        display.show_text(f"{line_id} LINE: No data", "RED")
        return
    
    # Parse data
    train_name = data.get('train', f'{line_id} TRAIN')
    status = data.get('status', 'Unknown')
    last_updated = data.get('last_updated', '')
    
    # Format timestamp
    time_str = transit.format_timestamp(last_updated) if hasattr(transit, 'format_timestamp') else "Time unknown"
    
    # Show header with line-specific color
    line_color = display.get_line_color(line_id)
    display.show_header(f"=== {train_name} ===", line_color)
    
    # Show basic status
    status_color = "GREEN" if status == "Good Service" else "YELLOW"
    display.show_text(f"Status: {status}", status_color)
    display.show_text(time_str, "WHITE")
    
    # Wait for header hold period
    while display.is_header_active():
        time.sleep_ms(100)
        # Check for interrupts during wait
        if check_button_interrupt():
            return
    
    # Show detailed info if service issues
    if status != "Good Service":
        display.extend_header_mode(30)  # Extend header for detailed info
        
        # Show trip and alert counts
        active_trips = data.get('active_trips', 0)
        active_alerts = data.get('active_alerts', 0)
        #display.show_text(f"Trips: {active_trips} Alerts: {active_alerts}")
        display.show_text(f"Alerts: {active_alerts}")
        
        # Show planned work
        planned_work = data.get('planned_work', [])
        if planned_work:
            display.show_text("PLANNED WORK:", "RED")
            for work_text in planned_work:
                if transit.display_planned_work:
                    transit.display_planned_work([work_text], display)
                else:
                    display.show_text(work_text[:display.max_chars], "YELLOW")
                    
                # Check for interrupts
                if check_button_interrupt():
                    return
        
        # Show delays and service changes
        delays = data.get('delays', [])
        if delays:
            display.show_text(f"Delays: {len(delays)}", "RED")
        
        service_changes = data.get('service_changes', [])
        if service_changes:
            display.show_text(f"Service Changes: {len(service_changes)}", "RED")
        
        display.end_header_mode()

def check_ppp_status():
    """Periodically check and display PPP status"""
    global ppp, cycle_count
    
    if not ppp or cycle_count % 10 != 0:  # Every 10 cycles
        return
    
    status = ppp.get_status()
    if display:
        display.show_text(status, "CYAN")
    
    # Auto-reconnect if disconnected
    if not ppp.is_connected():
        if display:
            display.show_text("Reconnecting PPP...", "YELLOW")
        ppp.auto_reconnect(max_attempts=2)

def check_memory():
    """Monitor memory usage"""
    try:
        free = gc.mem_free()
        if free < MEMORY_CONFIG['low_memory_threshold']:
            if display:
                display.show_text(f"Low memory: {free}", "YELLOW")
            # Force garbage collection
            gc.collect()
    except:
        pass

def blink_led():
    """Blink status LED if available"""
    if hardware and hardware.led:
        hardware.led.off()
        time.sleep_ms(100)
        hardware.led.on()

def startup_sequence():
    """Run startup sequence with all initializations"""
    success_count = 0
    
    # Initialize display first
    if init_display():
        success_count += 1
    
    # Initialize PPP
    if init_ppp():
        success_count += 1
    
    # Initialize hardware
    if init_hardware():
        success_count += 1
    
    # Initialize transit client  
    if init_transit_client():
        success_count += 1
    
    # Show startup summary
    if display:
        display.show_text(f"Initialized {success_count}/4 modules", "GREEN")
        time.sleep(TIMING['startup_delay'])
        display.clear_screen()
    
    return success_count >= 2  # Need at least display and one other module

def main_loop():
    """Main application loop"""
    global current_line_index, cycle_count, running
    
    print("Starting MTA Transit Monitor...")
    
    # Run startup sequence
    if not startup_sequence():
        print("Startup failed - insufficient modules initialized")
        return
    
    print("Startup complete, entering main loop...")
    
    try:
        while running:
            cycle_count += 1
            
            # Check for button interrupt at start of each cycle
            if check_button_interrupt():
                continue  # Skip to next iteration with new line
            
            # Show current line status
            current_line = TRANSIT_LINES[current_line_index]
            show_line_status(current_line)
            
            # Wait with interrupt checking
            interrupt_occurred = False
            wait_cycles = TIMING['line_display_duration'] * 10  # 100ms chunks
            
            for _ in range(wait_cycles):
                time.sleep_ms(100)
                if check_button_interrupt():
                    interrupt_occurred = True
                    break
            
            # Auto-advance to next line if no interrupt
            if not interrupt_occurred:
                current_line_index = (current_line_index + 1) % len(TRANSIT_LINES)
            
            # Periodic tasks
            check_ppp_status()
            blink_led()
            
            # Memory management
            if cycle_count % MEMORY_CONFIG['gc_interval'] == 0:
                check_memory()
                gc.collect()
            
    except KeyboardInterrupt:
        running = False
        if display:
            display.show_text("Stopping...", "RED")
        print("Application stopped by user")
    
    except Exception as e:
        running = False
        error_msg = f"Fatal error: {str(e)[:30]}"
        if display:
            display.show_text(error_msg, "RED")
        print(f"Fatal error: {e}")
    
    finally:
        cleanup()

def cleanup():
    """Clean up all resources"""
    global display, ppp, hardware, transit
    
    print("Cleaning up resources...")
    
    # Cleanup in reverse order of initialization
    if transit and hasattr(transit, 'cleanup'):
        transit.cleanup()
    
    if hardware and hasattr(hardware, 'cleanup'):
        hardware.cleanup()
    
    if ppp:
        ppp.cleanup()
    
    if display:
        display.cleanup()
    
    # Final garbage collection
    gc.collect()
    print("Cleanup complete")

# Test functions for development
def test_display():
    """Test display functionality"""
    if init_display():
        display.show_text("Display test", "GREEN")
        display.show_header("TEST HEADER", "BLUE", 3)
        display.show_text("Line 1", "WHITE")
        display.show_text("Line 2", "YELLOW")
        display.show_text("Line 3", "RED")
        return True
    return False

def test_ppp():
    """Test PPP connectivity"""
    init_display()
    return init_ppp()

def test_full_system():
    """Test all modules"""
    return startup_sequence()

def test_memory():
    """Test memory usage"""
    gc.collect()
    try:
        free = gc.mem_free()
        print(f"Free memory: {free} bytes")
        if display:
            display.show_text(f"Free: {free} bytes", "GREEN")
        return free
    except:
        print("Memory check failed")
        return None

# Entry point
if __name__ == "smain":
    main_loop()