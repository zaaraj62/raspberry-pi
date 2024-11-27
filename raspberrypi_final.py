import RPi.GPIO as GPIO
import time
import glob
from gpiozero import LED, Buzzer
import json, subprocess

# GPIO pin assignments
FIRE_SENSOR_PIN = 21
TEMP_SENSOR_PIN = 4
BUZZER_PIN = 17
LED_PIN = 18
BUTTON_PIN = 13

# Initialize components
led = LED(LED_PIN)
buzzer = Buzzer(BUZZER_PIN)

# ClickSend SMS configuration
username = 'zaaraashna'  # Add your username
api_key = 'D303CBE8-0DCE-C2FA-6B23-8B65DF1874ED'  # Add your API key
msg_to = '+12244156450'  # Recipient's phone number
msg_from = ''  # Sender's phone number or ID
msg_body = 'Fire detected! Immediate action required.'

# Temperature sensor setup
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

# Setup GPIO for fire sensor and button
GPIO.setmode(GPIO.BCM)
GPIO.setup(FIRE_SENSOR_PIN, GPIO.IN)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button setup with pull-up resistor

# Flag to prevent multiple SMS alerts
alert_sent = False

def send_sms():
    # Prepare SMS request using curl command
    request = {
        "messages": [
            {
                "source": "rpi",
                "from": msg_from,
                "to": msg_to,
                "body": msg_body
            }
        ]
    }
    request = json.dumps(request)

    # Build and execute curl command for SMS
    cmd = (
        f"curl https://rest.clicksend.com/v3/sms/send "
        f"-u {username}:{api_key} "
        f"-H \"Content-Type: application/json\" "
        f"-X POST --data-raw '{request}'"
    )
    print("Sending SMS...")  # Debug message
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, err = p.communicate()

    # Check and print debug output
    if p.returncode == 0:
        print("SMS sent successfully.")
        print("Output:", output.decode('utf-8'))
    else:
        print("Failed to send SMS.")
        print("Error:", err.decode('utf-8'))

def read_temp():
    with open(device_file, 'r') as f:
        lines = f.readlines()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f

def fire_detected_callback(channel):
    global alert_sent
    # Activate alarm if SMS hasn't been sent already
    if not alert_sent:
        led.on()
        buzzer.on()
        send_sms()
        alert_sent = True
    print("Fire detected! Alarm activated.")

def reset_alarm(channel):
    # Debug message to confirm button press detection
    print("Button pressed. Resetting alarm...")
    
    # Turn off alarm: LED and buzzer, and disable callbacks
    led.off()
    buzzer.off()
    
    # Clean up GPIO settings and exit program
    GPIO.cleanup()
    print("System reset and exited.")
    exit()  # Immediately exits the program

# Set up fire detection event
GPIO.add_event_detect(FIRE_SENSOR_PIN, GPIO.BOTH, bouncetime=300)
GPIO.add_event_callback(FIRE_SENSOR_PIN, fire_detected_callback)

# Set up button press to reset alarm
GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=reset_alarm, bouncetime=300)

# Main loop
try:
    while True:
        # Check for high temperature
        temp_c, temp_f = read_temp()
        print(f"Temperature detected: {temp_c:.2f}°C / {temp_f:.2f}°F")
        
        if temp_c and temp_c > 60:  # Threshold temperature, adjust as needed
            fire_detected_callback(FIRE_SENSOR_PIN)
        
        # Print no fire detected if no alarm is active
        if not alert_sent:
            print("No fire detected.")

        time.sleep(1)

except KeyboardInterrupt:
    print("System shutting down.")
finally:
    GPIO.cleanup()

