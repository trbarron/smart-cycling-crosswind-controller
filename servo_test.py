"""
Servo Test for Heart Rate Fan Controller
This script tests the SG90 servo motor at custom positions and displays
the corresponding heart rate that would trigger each position.

Usage:
    python3 servo_test.py
"""

import time
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
import RPi.GPIO as GPIO
import tm1637

SERVO_PIN = 18
DISPLAY_CLK_PIN = 17
DISPLAY_DIO_PIN = 27
MIN_PULSE_WIDTH = 0.5/1000  # 0.5ms
MAX_PULSE_WIDTH = 2.5/1000  # 2.5ms

# Heart rate mapping constants
MIN_HEART_RATE = 80
MAX_HEART_RATE = 150
MIN_SERVO_POS = -1.0
MAX_SERVO_POS = 1.0

def heart_rate_to_servo_position(heart_rate):
    """Convert heart rate to servo position"""
    hr_clamped = max(MIN_HEART_RATE, min(MAX_HEART_RATE, heart_rate))
    hr_normalized = (hr_clamped - MIN_HEART_RATE) / (MAX_HEART_RATE - MIN_HEART_RATE)
    return -1.0 + (hr_normalized * 2.0)

def servo_position_to_heart_rate(servo_position):
    """Convert servo position back to heart rate"""
    hr_normalized = (servo_position + 1.0) / 2.0
    heart_rate = MIN_HEART_RATE + (hr_normalized * (MAX_HEART_RATE - MIN_HEART_RATE))
    return heart_rate

def update_display(display, heart_rate, connected=True):
    """Update the TM1637 display with heart rate"""
    if not connected: return
        
    try:
        if not connected:
            display.show(" NA ")
        elif heart_rate > 0:
            if heart_rate >= 1000:
                display.show(" HI ")
            else:
                hr = int(heart_rate)
                if hr < 100:
                    display.show(f" {hr} ")
                else:
                    display.show(f"{hr} ")
        else:
            display.show("----")
            
    except Exception as e:
        print(f"Display update failed: {e}")

def test_servo():
    """Test the servo at custom positions with heart rate display"""
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    factory = PiGPIOFactory()
    servo = Servo(
        SERVO_PIN, 
        min_pulse_width=MIN_PULSE_WIDTH, 
        max_pulse_width=MAX_PULSE_WIDTH, 
        pin_factory=factory
    )
    
    display = tm1637.TM1637(clk=DISPLAY_CLK_PIN, dio=DISPLAY_DIO_PIN)
    display_connected = True
    
    try:
        display.brightness(3)
        display.show("----")
        time.sleep(1)
        display.show("TEST")
        time.sleep(1)
        print("Display initialized successfully")
    except Exception as e:
        print(f"Display initialization failed: {e}")
        display_connected = False
    
    print("=" * 60)
    print("Enhanced Servo Test - Heart Rate Fan Controller")
    print("=" * 60)
    print(f"Servo connected to GPIO {SERVO_PIN}")
    print(f"Display connected to CLK: GPIO {DISPLAY_CLK_PIN}, DIO: GPIO {DISPLAY_DIO_PIN}")
    print(f"Pulse width range: {MIN_PULSE_WIDTH*1000:.1f}ms - {MAX_PULSE_WIDTH*1000:.1f}ms")
    print(f"Heart rate range: {MIN_HEART_RATE} - {MAX_HEART_RATE} BPM")
    print(f"Servo position range: {MIN_SERVO_POS} to {MAX_SERVO_POS}")
    print()
    print("Commands:")
    print("  Enter servo position (-1.0 to 1.0)")
    print("  Enter 'h' followed by heart rate (e.g., 'h 75')")
    print("  Enter 'q' to quit")
    print("  Enter 'r' to run through heart rate range")
    print("=" * 60)
    
    try:
        while True:
            try:
                user_input = input("Enter command: ").strip().lower()
                
                if user_input == 'q':
                    break
                elif user_input == 'r':
                    print("Running through heart rate range...")
                    for hr in range(MIN_HEART_RATE, MAX_HEART_RATE + 1, 5):
                        servo_pos = heart_rate_to_servo_position(hr)
                        servo.value = servo_pos
                        
                        pulse_width = MIN_PULSE_WIDTH + (servo_pos + 1.0) * (MAX_PULSE_WIDTH - MIN_PULSE_WIDTH) / 2.0
                        
                        print(f"Heart Rate: {hr} BPM -> Servo: {servo_pos:.2f} (pulse: {pulse_width*1000:.1f}ms)")
                        
                        if display_connected:
                            update_display(display, hr)
                        
                        time.sleep(1)
                    continue
                elif user_input.startswith('h '):
                    try:
                        heart_rate = float(user_input[2:])
                        if heart_rate < MIN_HEART_RATE or heart_rate > MAX_HEART_RATE:
                            print(f"Heart rate must be between {MIN_HEART_RATE} and {MAX_HEART_RATE} BPM")
                            continue
                        
                        servo_pos = heart_rate_to_servo_position(heart_rate)
                        servo.value = servo_pos
                        
                        pulse_width = MIN_PULSE_WIDTH + (servo_pos + 1.0) * (MAX_PULSE_WIDTH - MIN_PULSE_WIDTH) / 2.0
                        
                        print(f"Heart Rate: {heart_rate:.1f} BPM -> Servo: {servo_pos:.2f} (pulse: {pulse_width*1000:.1f}ms)")
                        
                        if display_connected:
                            update_display(display, heart_rate)
                        
                        time.sleep(2)
                        continue
                    except ValueError:
                        print("Invalid heart rate. Use format 'h 75'")
                        continue
                else:
                    try:
                        position = float(user_input)
                        
                        if position < -1.0 or position > 1.0:
                            print("Position must be between -1.0 and 1.0")
                            continue
                        
                        servo.value = position
                        
                        heart_rate = servo_position_to_heart_rate(position)
                        
                        pulse_width = MIN_PULSE_WIDTH + (position + 1.0) * (MAX_PULSE_WIDTH - MIN_PULSE_WIDTH) / 2.0
                        
                        print(f"Servo: {position:.2f} -> Heart Rate: {heart_rate:.1f} BPM (pulse: {pulse_width*1000:.1f}ms)")
                        
                        if display_connected:
                            update_display(display, heart_rate)
                        
                        time.sleep(2)
                        
                    except ValueError:
                        print("Invalid input. Please enter a number between -1.0 and 1.0, 'h <heart_rate>', 'r', or 'q'")
            except KeyboardInterrupt:
                break
        
        print("Test completed!")
        
    except Exception as e:
        print(f"Error during servo test: {e}")
    finally:
        print("Cleaning up...")
        try:
            servo.mid()
            time.sleep(1)
            servo.close()
            
            if display_connected:
                display.show("DONE")
                time.sleep(1)
                display.show("    ")
            
            GPIO.cleanup()
            print("Cleanup completed")
        except:
            pass

if __name__ == "__main__":
    test_servo()