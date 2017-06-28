"""
This is a first attempt at making a pin controller for the RPi GPIO pins.
It is intended to be used to controll pins GPIO pins 28 and 29 in the NODE RPi 
baseboard design since these two pins control the two switches to the USB connections.
"""
import RPi.GPIO as GPIO

#dict that maps gpio pins to BCM pinout
GPIO_to_pin = {
				'0':1, '1':5, '2':9, '3':11,'4':15,
				'5':17, '6':21, '7':23, '8':27, '9':29,
				'10':33, '11':35, '12':45, '13':47,
				'14':51, '15':53, '16':57, '17':59,
				'18':63, '19':65, '20':69, '21':71,
				'22':75, '23':77, '24':81, '25':83,
				'26':87, '27':89, '28':28, '29':30,
				'30':29, '31':36, '32':46, '33':48,
				'34':30, '35':54, '36':58, '37':60,
				'38':64, '39':66, '40':70, '41':72,
				'39':66, '40':70, '41',72, '42':76,
				'43':78, '44':82, '45':84
				}

def readyBoard():
	"""
	Sets pins to follow broadcom chip-specific pin numbers, see pinout for reference
	"""
	GPIO.setmode(GPIO.BCM) 

def setPinOutput(pin):
	"""
	Sets pin as output pin

	Args:
		pin(string): GPIO pin number
	"""
	GPIO.setup(GPIO_to_pin[pin], GPIO.OUT) 

def setPinInput(pin):
	"""
	Sets pin as input pin

	Args:
		pin(string): GPIO pin number
	"""
	GPIO.setup(GPIO_to_pin[pin], GPIO.IN)

def setPinHigh(pin):
	"""
	Sets pin high

	Args:
		pin(string): GPIO pin number
	"""
	setPinOutput(pin)
	GPIO.output(GPIO_to_pin[pin], GPIO.HIGH)	

def setPinLow(pin):
	"""
	Sets pin low

	Args:
		pin(string): GPIO pin number
	"""
	setPinInput(pin)
	GPIO.output(GPIO_to_pin[pin], GPIO.LOW)

def readPin(pin):
	"""
	Reads pin

	Args:
		pin(string): GPIO pin number
	Returns:
		0 if low
		1 if high
	"""
	setPinInput(pin)
	if GPIO.input(GPIO_to_pin[pin]):
		return 1
	return 0

def make_bus_slave():
	"""
	Makes the pl bus a slave (connected to rpi thru usb 1.1)
	"""
	readyBoard()
	if not is_bus_slave():
		setPinLow('28')
		setPinLow('29')
	GPIO.cleanup() #unsure about this line

def make_bus_master():
	"""
	Makes the pl bus a master (connected to rpi thru usb 2.0) 
	"""
	readyBoard()
	if not is_bus_master():
		setPinHigh('28')
		setPinHigh('29')
	GPIO.cleanup() #unsure about this line

def is_bus_master():
	"""
	Checks if pl bus is master (connected to rpi thru usb 2.0)
	
	Returns:
		boolean
	"""
	return 0 == readPin('28') and 0 == readPin('29')

def is_bus_slave():
	"""
	Checks if pl bus is slave (connected to rpi thru usb 1.1)
	
	Returns:
		boolean
	"""
	return 1 == readPin('28') and 1 == readPin('29')
def main():
	try:
		make_bus_slave()
		if is_bus_slave():
			return 'P', 'Pl bus was made slave'
	except:
		return 'F', 'Pl bus was not made slave'

if __name__ == '__main__':
	main()
