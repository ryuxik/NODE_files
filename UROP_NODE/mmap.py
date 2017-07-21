"""
@Author: Santiago Munoz
@Date: 6/20/2017

	This is to test the comm to the FPGA using the memmory map. Assumes that PFGA board is Nero and Comm capable.
"""
import fl
import time
import ConfigParser

KEY_TO_LOC = {
				'PPM': 0, 'CTR': 1, 'ACC': 2, 'RCC': 3, 'LAC': 4, 'LRC': 5, 'FRC': 14, 'VER': 15,
				'PO1': 16, 'PO2': 17, 'PO3': 18, 'PO4': 19, 'HE1': 20, 'HE2': 21, 'CAL': 22, 'LTSa': 23,
				'LTSb': 24, 'LGA': 25, 'LCCa': 26, 'LCCb': 27, 'THRa': 28, 'THRb': 29, 'THRc': 30, 'PDI': 31,
				'FSMa': 32, 'FSMb': 33, 'FSMc': 34, 'ETX': 35, 'ERX': 36, 'SEC': 37, 'SCE': 37, 'SIE': 39,
				'SFL': 40, 'SST': 41, 'CC1a': 96, 'CC1b': 97, 'CC2a': 98, 'CC2b': 99, 'CC3a': 100, 'CC3b': 101,
				'CC4a': 102, 'CC4b': 103, 'TE1a': 104, 'TE1b': 105, 'TE2a': 106, 'TE2b': 107, 'TE3a': 108, 'TE3b': 109,
				'TE4a': 110, 'TE4b': 111, 'TE5a': 112, 'TE5b': 112, 'TE6a': 114, 'TE6b': 115, 'LTMa': 116, 'LTMb': 117}

class Tester(object):
	"""
	Tester class to send and read from FPGA registers following the memmory map
	"""
	def __init__(self, old_vid_pid, new_vid_pid):
		Config = ConfigParser.ConfigParser()
    	Config.read('args.ini')
		self.old_vid_pid = Config.get('ConnectionInfo', 'fpga_old_vid_pid')
		self.new_vid_pid = Config.get('ConnectionInfo', 'fpga_new_vid_pid')
		self.handle = self.start()
		self.on_code = 0x55
		self.off_code = 0x0F
		#format is id(6 bits?), address(1 byte), r/w (ro = 0b00, rw = 0b11), value = (varies)
		#below is example, must update, may not work
		#self.CTR = struct.pack('>sQBB','CTR',0x01, 0b11, 0x00)
		self.PPM = 0 # PPM order / Data
		self.CTR = 1 # Control
		self.ACC = 2 # Accepted commands
		self.RCC = 3 # Rejected commands
		self.LAC = 4 # Last acepted command
		self.LRC = 5 # Last rejected command
		self.FRC = 14 # Free running counter
		self.VER = 15 # Core version
		self.PO1 = 16 # Power on/off 1
		self.PO2 = 17 # Power on/off 2
		self.PO3 = 18 # Power on/off 3
		self.PO4 = 19 # Power on/off 4
		self.HE1 = 20 # Heater 1 on/off
		self.HE2 = 21 # Heater 2 on/off
		self.CAL = 22 # Power on/off 1
		self.LTSa = 23 # Temp  Set Point(MSB)
		self.LTSb = 24 # Temp  Set Poin  (LSB)
		self.LGA = 25 # Loop 
		self.LCCa = 26 # Current consumption (MSB)
		self.LCCb = 27 # Current consumption (LSB)
		self.THRa = 28 # Threshold configuration
		self.THRb = 29 # Threshold configuration
		self.THRc = 30 # Threshold configuration
		self.PDI = 31 # Power level
		self.FSMa = 32 # FSM configuration
		self.FSMb = 33 # FSM configuration
		self.FSMc = 34 # FSM configuration
		self.ETX = 35 # UART Tx
		self.ERX = 36 # UART Rx
		self.SEC = 37 # Error cycle
		self.SCE = 38 # Corrected Errors
		self.SIE = 39 # Inserted Errors
		self.SFL = 40 # Flags
		self.SST = 41 # Status
		self.CC1a = 96 # Current consumption 1 (MSB)
		self.CC1b = 97 # Current consumption 1 (LSB)
		self.CC2a = 98 # Current consumption 2 (MSB)
		self.CC2b = 99 # Current consumption 2 (LSB)
		self.CC3a = 100 # Current consumption 3 (MSB)
		self.CC3b = 101 # Current consumption 3 (LSB)
		self.CC4a = 102 # Current consumption 4 (MSB)
		self.CC4b = 103 # Current consumption 4 (LSB)
		self.TE1a = 104 # Temperature 1 (MSB)
		self.TE1b = 105 # Temperature 1 (LSB)
		self.TE2a = 106 # Temperature 2 (MSB)
		self.TE2b = 107 # Temperature 2 (LSB)
		self.TE3a = 108 # Temperature 3 (MSB)
		self.TE3b = 109 # Temperature 3 (LSB)
		self.TE4a = 110 # Temperature 4 (MSB)
		self.TE4b = 111 # Temperature 4 (LSB)
		self.TE5a = 112 # Temperature 5 (MSB)
		self.TE5b = 113 # Temperature 5 (LSB)
		self.TE6a = 114 # Temperature 6 (MSB)
		self.TE6b = 115 # Temperature 6 (LSB)
		self.LTMa = 116 # Measured temp (MSB)
		self.LTMb = 117 # Measured temp (LSB)
		self.addresses = 	{
							'PPM': (0,'rw'), 'CTR': (1,'rw'),'ACC': (2,'ro'), 'RCC': (3,'ro'),
							'LAC': (4,'ro'), 'LRC': (5,'ro'), 'FRC': (14,'ro'), 'VER': (15,'ro'),
							'PO1': (16,'rw'), 'PO2': (17,'rw'), 'PO3': (18,'rw'), 'PO4': (19, 'rw'),
							'HE1': (20,'rw'), 'HE2': (21,'rw'), 'CAL': (22,'rw'), 'LTSa': (23,'rw'),
							'LTSb': (24,'rw'), 'LGA': (25,'rw'), 'LCCa': (26,'rw'), 'LCCb': (27,'rw'),
							'THRa': (28,'rw'), 'THRb': (29,'rw'), 'THRc': (30,'rw'), 'PDI': (31,'ro'),
							'FSMa': (32,'rw'), 'FSMb': (33,'rw'), 'FSMc': (34,'rw'), 'ETX': (35,'rw'),
							'ERX': (36,'ro'), 'SEC': (37,'rw'), 'SCE': (37,'ro'), 'SIE': (39,'ro'),
							'SFL': (40,'ro'), 'SST': (41,'ro'), 'CC1a': (96,'ro'), 'CC1b': (97,'ro'),
							'CC2a': (98,'ro'), 'CC2b': (99,'ro'), 'CC3a': (100,'ro'), 'CC3b': (101,'ro'),
							'CC4a': (102,'ro'), 'CC4b': (103,'ro'), 'TE1a': (104,'ro'), 'TE1b': (105,'ro'),
							'TE2a': (106,'ro'), 'TE2b': (107,'ro'), 'TE3a': (108,'ro'), 'TE3b': (109, 'ro'),
							'TE4a': (110,'ro'), 'TE4b': (111,'ro'), 'TE5a': (112,'ro'), 'TE5b': (112,'ro'),
							'TE6a': (114,'ro'), 'TE6b': (115,'ro'), 'LTMa': (116,'ro'), 'LTMb': (117,'ro')
							}

	def start(self):
		"""
		Opens connection to FPGA board, and loads it with standard firmware.

		Returns:
			(handle): id representing fpga board
		"""

		fl.flInitialise(0)
		fl.flLoadStandardFirmware(old_vid_pid, new_vid_pid)
		time.sleep(3) #this should be fl.flAwaitDevice(), but according to past contributor, it didn't work
		handle = fl.flOpen(self.new_vid_pid)
		return handle

	def getAddress(self, name):
		"""
		Gets addresss of given name

		Args:
			name(string): name of address
		Returns:
			(int): address of name
		"""

		return self.addresses[name][0]

	def getType(self, name):
		"""
		Gets type of given name

		Args:
			name(string): name of address
		Returns:
			(string): type of address
		"""

		return self.addresses[name][1]

	def end(self):
		"""
		Closes connection to FPGA board.

		Args:
			fpga(NodeFPGA): object representing fpga board
		"""

		fl.flClose(self.handle) 

	def test_read(self, channel, expected):
		"""
		Compares data read from channel to what is expected from channel

		Args:
			channel(int): conduit channel to communicate through to fpga board
			expected(): expected response from communication through channel
		Returns:
			(boolean): True if expected matches what is read, else false
		"""

		return expected == fl.flReadChannel(self.handle, channel)

	def read(self, channel):
		"""
		Reads binary data from FPGA at channel

		Args:
			channel(int): channel to be read
		"""

		return fl.flReadChannel(self.handle, channel)

	def readAll(self):
		"""
		Reads all locations on memmory map and stores results.

		Returns:
			key_to_data(dict): Maps mem map location name to data read from that location
		"""

		key_to_data = {}
		for key in self.addresses:
			for value in self.addresses[key]:
				key_to_data[key] = self.read(value[0])
		return key_to_data

	def test_write(self, channel, data):
		"""
		Tests writing to a specified location in mem map using the channel and then checks the response of the board

		Args:
			channel(int): counduit channel to communicate to fpga board
			data(): data to be written to fpga board through specified channel
		Returns:
			(boolean): result from test_read
		"""

		fl.flWriteChannel(self.handle,channel, data)
		#not sure how to format data yet to test a read to loc that was written to
		#but the idea should be similar to this
		return self.test_read(channel, data)

	def test(self, progConfig):
		"""
		Main function to test reading and writing data to and from various addresses on the FPGA board

		Args:
			progConfig(): file to configure FPGA board
		Returns:
			res(list): list containig reports of passed and failed tests
		"""
		
		res = []
		ro = [(key, val[0]) for key in self.addresses for val in self.addresses[key] if val[1] == 'ro'] #creates tuples of read only locs with addr, (;NAME', addr)
		rw = [(key, val[0]) for key in self.addresses for val in self.addresses[key] if val[1] == 'rw'] #creates tuples of read/write locs with addr, ('NAME', addr)
		

		#implement tests using memmory map here and append results in correct format to res to be passed to RPI_a_test
		fl.flProgram(self.handle, progConfig)
		#fl.flLoadStandardFirmware(self.fpga.handle, progConfig)
		if fl.IsFPGARunning(self.handle):
			pass
			#need to check all mem map locs and either test rw or ro
			#then append ('P', 'Pass report'), or ('F', 'Fail report') to res

		self.end()
		return res


# :d