#!/usr/bin/python

import spidev
import time
import os
import sys
import RPi.GPIO as GPIO

# Define key
key = [[1,3],[0,2],[1,1]] #right 3 sec, left 2 sec, right 1 sec

# Define active
active = 0

# Define sensor channels
channel = 0

# Define delay between readings in sec
delay = 0.1

# Define array which stores first 5 variables
storage = []

# Define voltage and time tolerance
volt_tol = 0.01
time_tol = 0.5

# Define last reading storage
last_val = 0

# Define direction var 0 is left, 1 is right, 2 is none
direction = 2

# Define variable to track active: 0 inactive, 1 active
stop = 0

# Define mode var, 0 is secure 1 is unsecure
mode = 0

# Define Timer Variable in sec
timer = 0
active_timer = 0
total_timer = 0

# Setup GPIO for buttons
GPIO.setmode(GPIO.BCM)

# Setup pin numbers
button_pin = 17
mode_btn_pin = 18
lock_pin=22
unlock_pin=23

# Setup pins
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(mode_btn_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(lock_pin, GPIO.OUT)
GPIO.setup(unlock_pin, GPIO.OUT)

# Open SPI bus
spi = spidev.SpiDev() # create spi object
spi.open(0,0)
spi.max_speed_hz =  1000000

# RPI has one bus (#0) and two devices (#0 & #1)
# function to read ADC data from a channel
def GetData(channel): # channel must be an integer 0-7
        adc = spi.xfer2([1,(8+channel)<<4,0]) # sending 3 bytes
        data = ((adc[1]&3) << 8) + adc[2]
        return data

# Function to convert data to voltage level,
# Places: number of decimal places needed
def ConvertVolts(data,places):
	volts = (data * 3.3) / float(1023)
	volts = round(volts,places)
	return volts

# Define a sorting and removing direction
def Sort(array):
	temp = []
	for item in array:
		temp.append(item[1])
	temp.sort() 
	return temp

# Function that tests against the key based on the mode
def Test(input):
	print(input)

	valid = True

	if(input == []):
		print('Empty input')

	elif(len(input) != len(key)):
		print('Wrong number of inputs')

	elif (mode == 0):
		comp = key
		for i in range(0,len(comp)):
                	if not(comp[i][0] == input[i][0] and comp[i][1] <= input[i][1] + time_tol and comp[i][1] >= input[i][1] - time_tol):
                                valid = False
		if valid:
			print('Unlocking')
			# Unlock
	elif (mode == 1):
		comp = Sort(key)
		temp = Sort(input)
		for i in range(0,len(comp)):
                	if not(comp[i] <= temp[i] + time_tol and comp[i] >= temp[i] - time_tol):
                                valid = False
		if valid:
			print('Unlocking')
			# Unlock

# Function handles the button
def ActiveButton(channel):
	global active
	global active_timer
	global total_timer
	global timer
	global storage
	global last_val
	if(active == 0):
		active = 1
		timer = 0
		active_timer = 0
		total_timer = 0
		storage = []
		last_val = ConvertVolts(GetData(0),2)
		print('now active')
	else:
		if(direction != 2):
			storage.append([direction,timer])
		active = 0
		Test(storage)

def ChangeMode(channel):
	global mode 
	mode = (mode + 1) % 2
	print('mode is now: {}'.format(mode))

# Setup GPIO interrupts
GPIO.add_event_detect(button_pin, GPIO.FALLING, callback=ActiveButton, bouncetime=500)
GPIO.add_event_detect(mode_btn_pin, GPIO.FALLING, callback=ChangeMode, bouncetime=500)


try:
	
	while True:
		if(active == 1):
			temp = ConvertVolts(GetData(0),2)
			if (temp > last_val + volt_tol):
				if (direction == 1 and timer > 2 * delay):
					storage.append([direction,timer])
					timer = 0
					print('left save, timer reset')
				direction = 0
				active_timer = 0
				print('{}	going left'.format(timer))

			elif (temp < last_val - volt_tol):
				if  (direction == 0 and time > 2 * delay):
					storage.append([direction,timer])
					timer = 0
					print('right save, timer reset')
				direction = 1
				active_timer = 0
				print('{}	going right'.format(timer))

			else:
				if (direction != 2 and timer > 2 * delay):
					storage.append([direction, timer])
					timer = 0
					print('NM save, timer reset')
				direction = 2
				timer -= delay
				total_timer -= delay
				print('{}	NM'.format(timer))
				if (active_timer >= 2):
					active = 0
					print('not moving')
					Test(storage)

			last_val = temp

		# Wait before repeating loop
		timer += delay
		active_timer += delay
		total_timer += delay
		time.sleep(delay)

except Exception as e:
	print(e)

finally:
	spi.close()
	GPIO.cleanup()
