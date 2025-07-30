import s3lcd
import hardware.tft_config as tft_config
import vga1_bold_16x32 as big
import time

# Initialize TFT display
tft = tft_config.config(tft_config.WIDE)
tft.init()

# Pre-calculate constants
HEIGHT = tft.height()
WIDTH = tft.width()
FONT_HEIGHT = big.HEIGHT
FONT_WIDTH = big.WIDTH
MAX_CHARS = WIDTH // FONT_WIDTH - 2

# Define display areas
HEADER_HEIGHT = FONT_HEIGHT + 16  # Header area height (font + padding)
SCROLL_START_Y = HEADER_HEIGHT    # Where scrolling area begins
SCROLL_HEIGHT = HEIGHT - HEADER_HEIGHT  # Height of scrolling area
SCROLL_BOTTOM_Y = HEIGHT - FONT_HEIGHT  # Where new text appears

# Basic s3lcd colors
WHITE = s3lcd.WHITE
BLACK = s3lcd.BLACK
RED = s3lcd.RED
GREEN = s3lcd.GREEN
YELLOW = s3lcd.YELLOW
BLUE = s3lcd.BLUE
CYAN = s3lcd.CYAN
MAGENTA = s3lcd.MAGENTA

# Additional RGB565 colors (16-bit format: RRRRR GGGGGG BBBBB)
ORANGE = 0xFD20      # Orange
PURPLE = 0x8010      # Purple
PINK = 0xF81F        # Bright Pink
LIME = 0x07E0        # Bright Lime
NAVY = 0x000F        # Navy Blue
MAROON = 0x8000      # Maroon
OLIVE = 0x8400       # Olive
TEAL = 0x0410        # Teal
SILVER = 0xC618      # Silver
GRAY = 0x8410        # Gray
DARK_GRAY = 0x4208   # Dark Gray
LIGHT_BLUE = 0x841F  # Light Blue
LIGHT_GREEN = 0x87F0 # Light Green
LIGHT_RED = 0xFC10   # Light Red
GOLD = 0xFEA0        # Gold
BROWN = 0xA145       # Brown
INDIGO = 0x4810      # Indigo
VIOLET = 0x8818      # Violet
TURQUOISE = 0x471A   # Turquoise
CORAL = 0xFBEA       # Coral
SALMON = 0xFC0E      # Salmon
KHAKI = 0xF731       # Khaki
PLUM = 0xDD1B        # Plum
CRIMSON = 0xD8A7     # Crimson
FOREST_GREEN = 0x2444 # Forest Green
SKY_BLUE = 0x867D    # Sky Blue
HOT_PINK = 0xFB56    # Hot Pink
DEEP_PINK = 0xF8B2   # Deep Pink
SPRING_GREEN = 0x07EF # Spring Green
ROYAL_BLUE = 0x435C  # Royal Blue

# Create color list with names for display
colors = [
    (WHITE, "WHITE"),
    (RED, "RED"),
    (GREEN, "GREEN"),
    (BLUE, "BLUE"),
    (YELLOW, "YELLOW"),
    (CYAN, "CYAN"),
    (MAGENTA, "MAGENTA"),
    (ORANGE, "ORANGE"),
    (PURPLE, "PURPLE"),
    (PINK, "PINK"),
    (LIME, "LIME"),
    (NAVY, "NAVY"),
    (MAROON, "MAROON"),
    (OLIVE, "OLIVE"),
    (TEAL, "TEAL"),
    (SILVER, "SILVER"),
    (GRAY, "GRAY"),
    (DARK_GRAY, "DARK_GRAY"),
    (LIGHT_BLUE, "LIGHT_BLUE"),
    (LIGHT_GREEN, "LIGHT_GREEN"),
    (LIGHT_RED, "LIGHT_RED"),
    (GOLD, "GOLD"),
    (BROWN, "BROWN"),
    (INDIGO, "INDIGO"),
    (VIOLET, "VIOLET"),
    (TURQUOISE, "TURQUOISE"),
    (CORAL, "CORAL"),
    (SALMON, "SALMON"),
    (KHAKI, "KHAKI"),
    (PLUM, "PLUM"),
    (CRIMSON, "CRIMSON"),
    (FOREST_GREEN, "FOREST_GREEN"),
    (SKY_BLUE, "SKY_BLUE"),
    (HOT_PINK, "HOT_PINK"),
    (DEEP_PINK, "DEEP_PINK"),
    (SPRING_GREEN, "SPRING_GREEN"),
    (ROYAL_BLUE, "ROYAL_BLUE")
]

def clear_screen():
    """Clear the entire screen"""
    tft.fill(BLACK)
    tft.show()

def display_f_train_colors():
    """Loop through F Train text with different colors for F Train vs == brackets"""
    print(f"Starting F Train color loop with {len(colors)} colors...")
    
    # Clear screen initially
    clear_screen()
    
    color_index = 0
    
    # Fixed color for the "==" brackets (white)
    bracket_color = WHITE
    
    try:
        while True:
            # Get current color for "F Train"
            train_color_value, color_name = colors[color_index]
            
            # Clear screen
            clear_screen()
            
            # Display the text with different colors
            # "==" in white, "F Train" in cycling color, "==" in white
            x_pos = 8
            y_pos = 8
            
            # Draw "=="
            tft.text(big, "==", x_pos, y_pos, bracket_color, BLACK)
            x_pos += FONT_WIDTH * 2  # Move past "=="
            
            # Draw " F Train "
            tft.text(big, " F Train ", x_pos, y_pos, train_color_value, BLACK)
            x_pos += FONT_WIDTH * 9  # Move past " F Train "
            
            # Draw final "=="
            tft.text(big, "==", x_pos, y_pos, bracket_color, BLACK)
            
            # Display color name below in white
            tft.text(big, f"F Train: {color_name}", 8, 8 + FONT_HEIGHT + 8, WHITE, BLACK)
            tft.text(big, "Brackets: WHITE", 8, 8 + (FONT_HEIGHT + 8) * 2, WHITE, BLACK)
            
            # Display color index/total
            info_text = f"{color_index + 1}/{len(colors)}"
            tft.text(big, info_text, 8, 8 + (FONT_HEIGHT + 8) * 3, GRAY, BLACK)
            
            # Update display
            tft.show()
            
            # Print to console
            print(f"Color {color_index + 1}/{len(colors)}: F Train in {color_name} (0x{train_color_value:04X}), Brackets in WHITE")
            
            # Wait before next color
            time.sleep(2)
            
            # Move to next color
            color_index = (color_index + 1) % len(colors)
            
            # Optional: pause after completing full cycle
            if color_index == 0:
                print("Completed full F Train color cycle, starting over...")
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("F Train color loop stopped")
        clear_screen()
        tft.text(big, "Stopped", 8, 8, RED, BLACK)
        tft.show()

def test_f_train_static():
    """Display F Train text in a grid with different colors (if screen is large enough)"""
    clear_screen()
    
    # Calculate how many we can fit
    text_width = FONT_WIDTH * 13  # Approximate width for "== F Train =="
    colors_per_row = WIDTH // text_width
    rows_available = HEIGHT // FONT_HEIGHT
    
    print(f"Screen can display approximately {colors_per_row} F Train texts per row, {rows_available} rows")
    
    row = 0
    col = 0
    bracket_color = WHITE
    
    for i, (train_color_value, color_name) in enumerate(colors):
        if row >= rows_available:
            break
            
        x = col * text_width
        y = row * FONT_HEIGHT
        
        # Display abbreviated "==F==" with different colors
        tft.text(big, "==", x, y, bracket_color, BLACK)
        tft.text(big, "F", x + FONT_WIDTH * 2, y, train_color_value, BLACK)
        tft.text(big, "==", x + FONT_WIDTH * 3, y, bracket_color, BLACK)
        
        col += 1
        if col >= colors_per_row:
            col = 0
            row += 1
    
    tft.show()
    print(f"Displayed {min(len(colors), colors_per_row * rows_available)} F Train variations")

# Main execution
if __name__ == "test_colors_mx":
    print("TFT F Train Color Demo")
    print("Press Ctrl+C to stop")
    
    # You can choose which demo to run:
    # Option 1: Animated F Train color loop
    display_f_train_colors()
    
    # Option 2: Static grid display (uncomment to use instead)
    # test_f_train_static()
    # time.sleep(10)  # Display for 10 seconds