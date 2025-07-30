# Modular MicroPython Transit Monitor

A modular, memory-optimized transit monitoring system for ESP32 with TFT display and PPP connectivity.

## 📁 File Structure

```
project/
├── main.py              # Main application orchestrator
├── config.py            # Configuration constants and settings
├── display_manager.py   # TFT display operations and scrolling
├── ppp_manager.py       # PPP connectivity management
├── transit_client.py    # Transit API client and data processing
├── hardware_manager.py  # Button/LED hardware control
├── utils.py            # Utility functions and helpers
└── README.md           # This file
```

## 🚀 Quick Start

### 1. Upload Files to ESP32
```bash
# Using ampy or similar tool
ampy -p /dev/ttyUSB0 put config.py
ampy -p /dev/ttyUSB0 put display_manager.py
ampy -p /dev/ttyUSB0 put ppp_manager.py
ampy -p /dev/ttyUSB0 put transit_client.py
ampy -p /dev/ttyUSB0 put hardware_manager.py
ampy -p /dev/ttyUSB0 put utils.py
ampy -p /dev/ttyUSB0 put main.py
```

### 2. Run the Application
```python
# On ESP32 REPL
import main
# Or simply reset the device if main.py is set to auto-run
```

## ⚙️ Configuration

Edit `config.py` to customize settings:

```python
# Service URL
SERVICE_URL = "http://192.168.0.23:5000"

# PPP Settings
PPP_CONFIG = {
    'uart_id': 1,
    'baudrate': 9600,
    'tx_pin': 44,
    'rx_pin': 43,
    'timeout': 30
}

# Hardware Pins
PINS = {
    'led': 2,
    'button1': 0
}

# Transit Lines to Monitor
TRANSIT_LINES = ['F', 'R']  # Add more lines as needed
```

## 🧩 Module Usage

### Display Manager
```python
from display_manager import DisplayManager

display = DisplayManager()
display.show_text("Hello World!", "GREEN")
display.show_header("=== STATUS ===", "BLUE", hold_time=5)
```

### PPP Manager
```python
from ppp_manager import PPPManager
from display_manager import get_display_callback

display = DisplayManager()
callback = get_display_callback(display)

ppp = PPPManager(callback)
if ppp.connect():
    print("Connected!")
    print(ppp.get_status())
```

### Transit Client
```python
from transit_client import TransitClient

client = TransitClient()
data = client.fetch_line_data('F')
if data:
    print(f"F train status: {data['status']}")
```

### Hardware Manager
```python
from hardware_manager import HardwareManager

hardware = HardwareManager()
hardware.setup_button_interrupt()

# Check for button press in main loop
if hardware.check_interrupt():
    print("Button pressed!")
```

## 🔧 Advanced Usage

### Custom Display Callback
```python
def my_display_callback(text, color):
    print(f"[{color}] {text}")

ppp = PPPManager(my_display_callback)
```

### Memory Monitoring
```python
from utils import memory_info, check_low_memory

# Get memory information
mem = memory_info()
print(f"Free memory: {mem['free']} bytes")

# Check for low memory with warning
if check_low_memory(display_callback):
    print("Memory is low!")
```

### Caching Control
```python
from transit_client import TransitClient

client = TransitClient()

# Clear cache to force fresh data
client.clear_cache()

# Get client statistics
stats = client.get_client_stats()
print(f"API requests made: {stats['request_count']}")
```

## 🧪 Testing Individual Modules

### Test Display
```python
import main
main.test_display()
```

### Test PPP Connection
```python
import main
main.test_ppp()
```

### Test Memory Usage
```python
import main
free_bytes = main.test_memory()
```

### Test All Systems
```python
import main
main.test_full_system()
```

### Individual Module Tests
```python
# Test transit client
from transit_client import quick_line_test
quick_line_test('F')

# Test hardware
from hardware_manager import quick_led_test
quick_led_test()

# Test PPP
from ppp_manager import quick_connect
success, ppp_instance = quick_connect()
```

## 🛠️ Customization

### Adding New Transit Lines
1. Edit `TRANSIT_LINES` in `config.py`
2. Add color mapping in `SUBWAY_LINE_COLORS` if needed
3. Restart the application

### Custom Colors
```python
# In config.py, modify SUBWAY_LINE_COLORS
SUBWAY_LINE_COLORS = {
    'F': 'ORANGE',
    'R': 'YELLOW',
    'NEW_LINE': 'PURPLE'  # Add custom mapping
}
```

### Adjusting Timing
```python
# In config.py
TIMING = {
    'line_display_duration': 15,  # Show each line for 15 seconds
    'startup_delay': 3,           # 3 second startup delay
    'interrupt_debounce_ms': 300  # Faster button response
}
```

## 🔍 Debugging

### Enable Verbose Logging
```python
# Add to main.py or any module
import utils
utils.print_memory_status()  # Print memory info

# Get system information
info = utils.get_system_info()
print(info)
```

### Monitor Network Status
```python
# In main loop, check PPP status more frequently
def debug_network():
    if ppp:
        status = ppp.get_status(detailed=True)
        print(f"PPP Status: {status}")
```

### Display Debugging Info
```python
# Check display information
if display:
    info = display.get_display_info()
    print(f"Display info: {info}")
```

## 📊 Memory Optimization

### Memory-Efficient Patterns
```python
# Use lazy imports
def load_heavy_module():
    import heavy_module
    result = heavy_module.do_work()
    del heavy_module  # Remove reference
    gc.collect()
    return result

# Limit data processing
data = fetch_large_dataset()
processed = process_first_n_items(data, n=5)  # Process only what you need
del data  # Free original data
```

### Monitor Memory Usage
```python
from utils import check_low_memory, format_memory

# Regular memory checks
if cycle_count % 10 == 0:
    mem_info = memory_info()
    if mem_info['is_low']:
        print(f"Low memory: {format_memory(mem_info['free'])}")
        gc.collect()
```

## 🔒 Error Handling

Each module includes comprehensive error handling:

- **Network errors**: Automatic retry with exponential backoff
- **Display errors**: Fallback to console output
- **Hardware errors**: Graceful degradation
- **Memory errors**: Automatic garbage collection

### Custom Error Handling
```python
try:
    result = risky_operation()
except Exception as e:
    if display:
        display.show_text(f"Error: {str(e)[:20]}", "RED")
    else:
        print(f"Error: {e}")
```

## 🔄 Automatic Recovery

The system includes automatic recovery features:

- **PPP reconnection**: Automatic retry on connection loss
- **Service health monitoring**: Regular health checks with fallback
- **Memory management**: Automatic garbage collection
- **Cache management**: Automatic cache cleanup and size limits

## 📈 Performance Tips

1. **Use caching**: Transit data is cached for 30 seconds by default
2. **Limit display updates**: Don't update display too frequently
3. **Monitor memory**: Regular garbage collection prevents crashes
4. **Lazy loading**: Import modules only when needed
5. **Text truncation**: Long texts are automatically truncated

## 🆘 Troubleshooting

### Common Issues

**Display not working**
- Check hardware connections
- Verify TFT library installation
- System falls back to console output

**PPP connection fails**
- Check UART pins and baudrate
- Verify PPP device is connected
- Check power supply

**Memory errors**
- Reduce cache timeout in config
- Limit number of transit lines
- Increase garbage collection frequency

**Service unavailable**
- Check SERVICE_URL in config
- Verify network connectivity
- System continues with cached data

### Getting Help

Check the individual module files for detailed documentation and additional configuration options. Each module is designed to be independent and well-documented.