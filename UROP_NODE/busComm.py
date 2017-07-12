"""
@Author: Santiago Munoz
@Date: 6/13/2017

	This controls communication between the RPI CM3 and pl bus. See pyusb for documentation. 
"""
import usb.core

class Connection:
	"""
	Class to handle communication over USB with devices
	"""
	def __init__(self, vid, pid, packet_size, timeout, wendpoint, rendpoint, isMaster=False, debug=False):
		self.isMaster = isMaster
		self.vid = vid
		self.pid = pid
		self.d = self.findDevice()
		self.packet_size = packet_size
		self.data = 'foo' #holds data the bus should recieve from the pi
		self.received = 'bar' #holds data the pi recieves from the bus
		self.debug = debug
		self.timeout = timeout
		self.writeEndpoint = wendpoint
		self.readEndpoint = rendpoint
		if self.debug:
			logDevice(self.d)

	def findDevice(self): 
		"""
		Finds usb device with given vendor and product id and configures it.

		Returns:
			(usb.core.Device): object representing USB device
		"""

		device = usb.core.find(idVendor=self.vid, idProduct=self.pid)
		device.set_configuration() #tries to set first configuration available
		if device is None:
			raise ConnectionError('F', 'Connection to <', self.vid,':', self.pid, '> failed.')
		return device

	def logDevice(d):
		"""
		Prints device attributes for debugging purposes.
		"""
		print('\nbLength: ', d.bLength)
		print('\nbDescriptorType: ', d.bDescriptorType)
		print('\nbEndpointAddress: ', d.bEndpointAddress)
		print('\nbmAttributes: ', d.bmAttributes)
		print('\nwMaxPacketSize: ', d.wMaxPacketSize)
		print('\nbInterval: ', d.bInterval)
		print('\nbRefresh: ', d.bRefresh)
		print('\nbSynchAddress: ', d.bSynchAddress)
		print('\nextra_descriptors: ', d.extra_descriptors)

	def sendData(self): 
		"""
		Sends stored data to device
		"""
		
		to_send = self.data
		assert len(self.d.write(self.wendpoint, to_send, self.timeout)) == len(to_send)

	def updateData(self, newData): 
		"""
		Updates stored data and sends it

		Args:
			newData(varies): new data to be sent through connection
		"""
		self.data = newData
		self.sendData()

	def updateReceived(self): 
		"""
		Updates message received from device
		"""
		r = self.d.read(self.rendpoint,self.packet_size,self.timeout) #replace 0x81 with correct endpoint
		self.received = ''.join([chr(i) for i in r]) # change this line to format message received appropriately

	def testConnection(self, to_send, to_receive):
		try:
			s = self.updateData(to_send)
			self.updateReceived()
			r = self.received
			if r == to_receive:
				return 'P','Device: ', self.device, ' is connected'

		except:
			raise ConnectionError('F','Connection to ', self.d, ' failed.')


def main():
	pass

if __name__ == '__main__':
	main()