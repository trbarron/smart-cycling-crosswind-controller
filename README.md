# Heart Rate Fan Controller

A Raspberry Pi-based automatic fan controller that adjusts fan speed based on your real-time heart rate, similar to the [wahoo KICKR Headwind](https://www.wahoofitness.com/devices/indoor-cycling/accessories/kickr-headwind-buy). Ideal for indoor cycling.

## Features

- **Real-time heart rate monitoring** via Colmi R02 smart ring
- **Automatic fan speed control** using servo-controlled AC motor
- **Live heart rate display** on 4-digit LED display

## Hardware Components

### Required Parts

- **Raspberry Pi Zero W 2** - Main controller
- **Colmi R02 Smart Ring** - Heart rate sensor ([Amazon](https://www.aliexpress.us/w/wholesale-colmi-smart-ring.html?spm=a2g0o.productlist.search.0))
- **SG90 Servo Motor** - Fan speed control ([Amazon](https://www.amazon.com/s?k=sg90+servo+motor))
- **TM1637 4-Digit Display** - Heart rate display ([Amazon](https://www.amazon.com/s?k=tm1637+4+digit+display))
- **AC Motor/Fan** - The actual cooling fan

### Wiring Diagram

```
Raspberry Pi Zero W 2 Connections:

SG90 Servo:
├── Brown (GND)   → Pin 6 (Ground)
├── Red (VCC)     → Pin 2 (5V)
└── Orange (PWM)  → Pin 12 (GPIO 18)

TM1637 Display:
├── VCC → Pin 4 (5V)
├── GND → Pin 9 (Ground)
├── CLK → Pin 11 (GPIO 17)
└── DIO → Pin 13 (GPIO 27)

Colmi R02 Ring:
└── Bluetooth connection (no wires needed)
```

## Software Setup

### Installation

1. **Clone or download the project files**
   ```bash
   mkdir heartrate-fan && cd heartrate-fan
   # Copy the Python script to this directory
   ```

2. **Install system dependencies**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-dev bluetooth bluez
   sudo systemctl enable bluetooth
   sudo systemctl start bluetooth
   ```

3. **Install Python packages**
   ```bash
   pip3 install RPi.GPIO gpiozero pigpio tm1637-rpi
   sudo pip3 install colmi-r02-client
   ```

4. **Enable pigpio daemon**
   ```bash
   sudo systemctl enable pigpiod
   sudo systemctl start pigpiod
   ```

5. **Create logs directory**
   ```bash
   mkdir logs
   ```

### Colmi R02 Ring Setup

1. **Pair the ring with your Raspberry Pi**
   ```bash
   sudo bluetoothctl
   # In bluetoothctl:
   scan on
   # Wait for your ring to appear (5B:62:EE:DA:AD:40 or similar)
   pair [RING_MAC_ADDRESS]
   trust [RING_MAC_ADDRESS]
   exit
   ```

2. **Update the MAC address in the code**
   - Find your ring's MAC address:
   ```bash
   colmi_r02_utils --scan
   ```
   - Edit the `COLMI_ADDRESS` variable in the Python script with your ring's address

3. **Test the connection**
   ```bash
   colmi_r02_client --address=YOUR_RING_MAC get-real-time-heart-rate
   ```

## Configuration

### Heart Rate Ranges
Adjust these constants in the code to match your fitness level:

```python
MIN_HEART_RATE = 50   # BPM - minimum for fan activation
MAX_HEART_RATE = 120  # BPM - maximum for full fan speed
```

### Fan Speed Control
Servo position ranges (adjust based on your motor setup):

```python
MIN_SERVO_POS = -1.0  # Minimum fan speed position
MAX_SERVO_POS = 1.0   # Maximum fan speed position
```

### Update Frequency
```python
UPDATE_INTERVAL = 90  # Seconds between heart rate readings
```

## How It Works

1. **Heart Rate Monitoring**: The Colmi R02 ring continuously monitors your heart rate via Bluetooth
2. **Speed Calculation**: Heart rate is mapped to a servo position (higher HR = faster fan)
3. **Servo Control**: SG90 servo adjusts the AC motor speed controller
4. **Display Update**: Current heart rate is shown on the 4-digit display
5. **Error Handling**: Automatic Bluetooth reconnection and failure recovery
