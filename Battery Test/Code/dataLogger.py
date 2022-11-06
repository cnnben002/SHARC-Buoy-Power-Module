#Author: Benjamin Connolly
#Date: 04/10/2022
#Project: SHARC Buoy - Data logger

#Imports
import time
import board
import os
import adafruit_dht
import RPi.GPIO as GPIO
from ina219 import INA219
from ina219 import DeviceRangeError
from datetime import datetime
from getkey import getkey
from sys import exit

#Reading INA219 data
def readINA(SHUNT_OHMS, MAX_EXPECTED_AMPS):
    ina1 = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=0x40)
    ina1.configure(ina1.RANGE_16V)
    ina2 = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=0x41)
    ina2.configure(ina2.RANGE_16V)

    ina1.wake()
    ina2.wake()

    data = dict()

    try:
        data[0] = round(ina1.voltage(), 3)
        data[1] = round(ina1.current(), 3)
        data[2] = round(ina1.power(), 3)
        data[3] = round(ina1.shunt_voltage(), 3)
        data[4] = round(ina2.voltage(), 3)
        data[5] = round(ina2.current(), 3)
        data[6] = round(ina2.power(), 3)
        data[7] = round(ina2.shunt_voltage(), 3)
    except DeviceRangeError as e:
        print(e)

    ina1.sleep()
    ina2.sleep()

    return data

#Main code
if __name__ == "__main__":
    print("Executing code...")
    print("Setting up...")

    #Initial setup
    DHT = adafruit_dht.DHT22(board.D4)
    temperature = DHT.temperature
    humidity = DHT.humidity

    SHUNT_OHMS = 0.1
    MAX_EXPECTED_AMPS = 0.7

    LED1_PIN = 22
    LED2_PIN = 23
    LED3_PIN = 24
    RELAY_PIN = 5
    BUZZER_PIN = 6
    CONTROL_PIN = 18

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(LED1_PIN, GPIO.OUT)
    GPIO.setup(LED2_PIN, GPIO.OUT)
    GPIO.setup(LED3_PIN, GPIO.OUT)
    GPIO.setup(RELAY_PIN, GPIO.OUT)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.setup(CONTROL_PIN, GPIO.OUT)

    GPIO.output(LED1_PIN, GPIO.LOW)
    GPIO.output(LED2_PIN, GPIO.LOW)
    GPIO.output(LED3_PIN, GPIO.LOW)
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

    #Starting PWM Control
    CONTOL_PWM = GPIO.PWM(CONTROL_PIN, 8000)
    CONTOL_PWM.start(0)

    prevTime = time.time()
    dc = 0

    print("Setting up file...")

    #Creating CSV data log file
    f = open("data.csv", "a")
    f.write(str(datetime.now()) + "\n")
    f.write("Time(s),Humidity(%),Temperature(C),")
    f.write("Voltage1(V),Current1(mA),Power1(mW),ShuntVoltage1(mV),")
    f.write("Voltage2(V),Current2(mA),Power2(mW),ShuntVoltage2(mV)\n")
    f.close()

    print("Logging data...")

    while True:
        #Reading environmental data
        try:
            temperature = DHT.temperature
            humidity = DHT.humidity
            print(temperature)
            print(humidity)
            data = dict()
            data[0] = round(humidity, 3)
            data[1] = round(temperature, 3)
            break

        except RuntimeError as error:
            print(error.args[0])
            time.sleep(0.1)
            continue

        except Exception as error:
            DHT.exit()
            raise error

    try:
        while(True):
            #Reading data from INA219's
            data = readINA(SHUNT_OHMS, MAX_EXPECTED_AMPS)

            #Updating visual indicators based on current reading
            # and updating the duty cycle to adjust the current
            if data[1] <= 350:
                GPIO.output(LED1_PIN, GPIO.HIGH)
                GPIO.output(LED2_PIN, GPIO.LOW)
                GPIO.output(LED3_PIN, GPIO.LOW)
                dc += 0.01

            elif round(data[1]) == 350:
                GPIO.output(LED1_PIN, GPIO.LOW)
                GPIO.output(LED2_PIN, GPIO.HIGH)
                GPIO.output(LED3_PIN, GPIO.LOW)

            elif data[1] >= 350:
                GPIO.output(LED1_PIN, GPIO.LOW)
                GPIO.output(LED2_PIN, GPIO.LOW)
                GPIO.output(LED3_PIN, GPIO.HIGH)
                dc -= 0.01

            if data[1] >= 700:
                GPIO.output(RELAY_PIN, GPIO.LOW)
                GPIO.output(BUZZER_PIN, GPIO.HIGH)
                print("limits exceeded - shutting down experiment...")
                break

            #Ensuring that the suty cycle is kept between 0 and 100
            if dc > 100:
                dc = 100

            elif dc < 0:
                dc = 0

            CONTOL_PWM.ChangeDutyCycle(dc)

            #Logging data every 10 seconds
            if (round(time.time())-prevTime) >= 10:
                f = open("data.csv", "a")

                s = str(round(time.time())) + "," + str(humidity) + "," + str(temperature) + ","
                s += str(data[0]) + "," + str(data[1]) + "," + str(data[2]) + "," + str(data[3]) + ","
                s += str(data[4]) + "," + str(data[5]) + "," + str(data[6]) + "," + str(data[7]) + "\n"

                f.write(s)
                f.close()

                prevTime = time.time()

            #Printing values to the terminal
            os.system('clear')
            print("Voltage: ", data[0])
            print("Current: ", data[1])
            print("Power: ", data[2])
            print("S-Voltage: ", data[3])
            print("Duty-cycle: ", dc)
            print()

            #Giving a slight delay to allow all processes to run
            time.sleep(0.2)

    #Exiting the program if ^C is pressed
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("Exited.")