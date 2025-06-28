"""
Heart Rate Fan Controller for Raspberry Pi Zero W 2
Connects Colmi R02 smart ring to SG90 servo controlling AC motor speed
Displays heart rate on TM1637 4-digit display

Hardware Setup:
- SG90 Servo: 
  * Brown wire (GND) -> Pin 6 (Ground)
  * Red wire (VCC) -> Pin 2 (5V)
  * Orange wire (Signal) -> Pin 12 (GPIO 18)
- TM1637 4-Digit Display:
  * VCC -> Pin 4 (5V)
  * GND -> Pin 9 (Ground)
  * CLK -> Pin 11 (GPIO 17)
  * DIO -> Pin 13 (GPIO 27)
- Colmi R02: Bluetooth connection
"""

import time
import json
import logging
import subprocess
import RPi.GPIO as GPIO
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
import tm1637

COLMI_ADDRESS = "5B:62:EE:DA:AD:40"
SERVO_PIN = 18
DISPLAY_CLK_PIN = 17
DISPLAY_DIO_PIN = 27
UPDATE_INTERVAL = 90
MAX_CONSECUTIVE_FAILURES = 3

MIN_HEART_RATE = 80
MAX_HEART_RATE = 150
MIN_SERVO_POS = -1.0
MAX_SERVO_POS = 1.0

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/heartrate_fan.log'),
        logging.StreamHandler()
    ]
)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

class HeartRateFanController:
    def __init__(self):
        factory = PiGPIOFactory()
        self.servo = Servo(SERVO_PIN, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, pin_factory=factory)
        self.display = tm1637.TM1637(clk=DISPLAY_CLK_PIN, dio=DISPLAY_DIO_PIN)
        self.running = True
        self.current_heart_rate = 0
        self.current_servo_pos = 0
        self.display_connected = True
        self.consecutive_failures = 0
        
        self.servo.min()
        
        try:
            self.display.brightness(3)
            self.display.show("----")
            time.sleep(1)
            self.display.show("INIT")
            logging.info("Display initialized successfully")
        except Exception as e:
            logging.warning(f"Display initialization failed: {e}")
            self.display_connected = False
        
        # Reset Bluetooth at startup
        self.reset_bluetooth()
        
        logging.info("Heart Rate Fan Controller initialized")
    
    def reset_bluetooth(self):
        try:
            logging.info("Attempting to reset Bluetooth adapter...")
            self.display.show(" BT ")
            
            subprocess.run(["sudo", "hciconfig", "hci0", "down"], check=True)
            time.sleep(2)
            
            subprocess.run(["sudo", "hciconfig", "hci0", "up"], check=True)
            time.sleep(2)
            
            logging.info("Bluetooth adapter reset complete")
            return True
        except Exception as e:
            logging.error(f"Failed to reset Bluetooth: {e}")
            return False
    
    def get_heart_rate(self):
        try:
            cmd = [
                "colmi_r02_client",
                f"--address={COLMI_ADDRESS}",
                "get-real-time-heart-rate"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines:
                    if line.startswith('[') and line.endswith(']'):
                        hr_values = json.loads(line)
                        if hr_values:
                            self.consecutive_failures = 0
                            return hr_values[-1]
            
            # Check for specific error conditions
            if "BleakDeviceNotFoundError" in result.stderr:
                logging.warning("Ring not found - will retry immediately")
                self.consecutive_failures += 1
                return None
            elif "BleakError: Not connected" in result.stderr:
                logging.warning("Bluetooth connection lost - will retry immediately")
                self.consecutive_failures += 1
                return None
            elif "TimeoutError" in result.stderr:
                logging.warning("Reading timed out - will retry immediately")
                self.consecutive_failures += 1
                return None
                
            logging.warning(f"Failed to get heart rate: {result.stderr}")
            self.consecutive_failures += 1
            return None
            
        except subprocess.TimeoutExpired:
            logging.error("Heart rate reading timed out")
            self.consecutive_failures += 1
            return None
        except Exception as e:
            logging.error(f"Error getting heart rate: {e}")
            self.consecutive_failures += 1
            return None
    
    def heart_rate_to_servo_position(self, heart_rate):
        hr_clamped = max(MIN_HEART_RATE, min(MAX_HEART_RATE, heart_rate))
        hr_normalized = (hr_clamped - MIN_HEART_RATE) / (MAX_HEART_RATE - MIN_HEART_RATE)
        # Map to servo range: -1.0 (80 BPM) to 1.0 (150 BPM)
        return -1.0 + (hr_normalized * 2.0)
    
    def update_display(self, heart_rate, connected=True):
        if not self.display_connected: return
            
        try:
            if not connected:
                self.display.show(" NA ")
            elif heart_rate > 0:
                if heart_rate >= 1000:
                    self.display.show(" HI ")
                else:
                    hr = int(heart_rate)
                    if hr < 100:
                        self.display.show(f" {hr} ")
                    else:
                        self.display.show(f"{hr} ")
            else:
                self.display.show("----")
                
        except Exception as e:
            logging.warning(f"Display update failed: {e}")
    
    def update_fan_speed(self, heart_rate):
        servo_pos = self.heart_rate_to_servo_position(heart_rate)
        
        if abs(servo_pos - self.current_servo_pos) > 0.1:
            self.servo.value = servo_pos
            self.current_servo_pos = servo_pos
            logging.info(f"Heart rate: {heart_rate:.1f} BPM -> Servo position: {servo_pos:.2f}")
        
        self.update_display(heart_rate, connected=True)
    
    def monitor_heart_rate(self):
        logging.info("Starting heart rate monitoring...")
        
        while self.running:
            try:
                heart_rate = self.get_heart_rate()
                
                if heart_rate is not None:
                    self.current_heart_rate = heart_rate
                    self.update_fan_speed(heart_rate)
                    logging.info(f"Heart Rate: {heart_rate}")
                    time.sleep(UPDATE_INTERVAL)
                else:
                    logging.warning("No heart rate data received")
                    self.update_display(0, connected=False)
                    
                    if self.consecutive_failures >= 2:
                        if self.reset_bluetooth():
                            self.consecutive_failures = 0
                        time.sleep(5)
                    else:
                        time.sleep(3)
                
            except KeyboardInterrupt:
                logging.info("Shutdown requested by user")
                self.stop()
                break
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(UPDATE_INTERVAL)
    
    def stop(self):
        self.running = False
        self.servo.min()
        
        if self.display_connected:
            try:
                self.display.show("L8TR")
                time.sleep(1)
                self.display.show("    ")
            except:
                pass
        
        self.servo.close()
        logging.info("Heart Rate Fan Controller stopped")

def main():
    try:
        controller = HeartRateFanController()
        controller.monitor_heart_rate()
    except KeyboardInterrupt:
        controller.stop()
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
