"""
@Author: Santiago Munoz
@Date: 6/20/2017

	This is to test the comm to the FPGA using the memmory map. Assumes that PFGA board is Nero and Comm capable.
"""
import fl
import time
from node import NodeFPGA
import struct

class tester(object):
	"""
	Tester class to send and read from FPGA registers following the memmory map
	"""
	def __init__(self, old_vid_pid, new_vid_pid):
		self.old_vid_pid = old_vid_pid
		self.new_vid_pid = new_vid_pid
		self.fpga = self.start()
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
		self.THRb = 29 # 
		self.THRc = 30 # 
		self.PDI = 31 # Power level
		self.FSMa = 32 # FSM configuration
		self.FSMb = 33 # 
		self.FSMc = 34 # 
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

	def start(self):
		#creates NodeFGA object and opens connection to FPGA board
		fl.flInitialise(0)
		fl.flLoadStandardFirmware(old_vid_pid, new_vid_pid)
		#this should be fl.flAwaitDevice, but according to past contributor, it didn't work
		time.sleep(3)
		handle = fl.flOpen(self.new_vid_pid)
		return NodeFPGA(handle)

	def end(self, fpga):
		#closes connection to FPGA board
		fl.flClose(fpga.handle) 

	def test_read(fpga, channel, expected):
		return expected == fl.flReadChannel(fpga.handle, channel)

	def test_write(fpga, channel, data):
		fl.flWriteChannel(fpga.handle,channel, data)
		#not sure how to format data yet to test a read to loc that was written to
		#but the idea should be similar to this
		return test_read(fpga, channel, data)

	def test(self, vid_pid_did, progConfig):
		res = []
		
		#implement tests using memmory map here and append results in correct format to res to be passed to RPI_a_test
		fl.flProgram(self.fpga.handle, progConfig)
		#fl.flLoadStandardFirmware(self.fpga.handle, progConfig)
		if fl.IsFPGARunning(self.fpga.handle):
			pass
			#need to check all mem map locs and either test rw or ro
			#then append ('P', 'Pass report'), or ('F', 'Fail report') to res

		self.end(self.fpga)
		return res
