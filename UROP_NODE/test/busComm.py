"""
@Author: Santiago Munoz
@Date: 6/13/2017

	This controls communication between the RPI CM3 and connected devices. Requires installation of python-serial.
"""
import serial

class serialW:
	"""
	class to handle communication with device
	"""
	def __init__(self, d, isMaster=False):
		self.isMaster = isMaster
		self.device = d #port directory, see main for example
		self.b_rate_def = 115200 #fix with proper baudrate
		self.d_timeout = 3.0 #default timeout on connection
		self.bytes = 10 #expected bytes per comm 
		self.s = serial.Serial(d, baudrate=b_rate_def, timeout=d_timeout)
		self.data = 'foo' #holds data the bus should recieve from the pi
		self.received = 'bar' #holds data the pi recieves from the bus

	def sendData(self): #sends stored data to device
		d = "\r\n"+self.data
		self.s.write(d)

	def updateData(self, newData): #updates stored data
		self.data = newData

	def updateReceived(self): #updates message recieved from device
		r = self.s.read(self.bytes)
		self.recieved = r

	def testConnection(self):
		try:
			n = self.s.read(self.bytes)
			if n:
				return 'P','Device: ', self.device, ' is connected'

		except:
			raise ConnectionError('F','Connection to ', self.d, ' failed.')

if __name__ == "__main__":
	p = serialW("/dev/ttyAMA0") #replace with correct device
	while True: #replace loop with proper logic to handle communication
		p.sendData() #this should send data from pi
		p.updateReceived() #check in this funct for special signals
		#p.updateData(), should get new pi info at this step
		

