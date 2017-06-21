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
	def __init__(self, vid_pid_did):
		self.vid_pid_did = vid_pid_did
		self.fpga = self.start()
		self.on_code = 0x55
		self.off_code = 0x0F
		#format is id(6 bits?), address(1 byte), r/w (ro = 0b00, rw = 0b11), value = (varies)
		#below is example, must update, may not work
		self.CTR = struct.pack('>sQBB','CTR',0x01, 0b11, 0x00)
		self.ACC = 0b0000010
		self.RCC = 0b0000011
		self.LAC = 0b0000100
		self.LRC = 0b0000101
		self.FRC = 0b0001110
		self.VER = 0b0001111
		self.PO1 = 0b0010000
		self.PO2 = 0b0010001
		self.PO3 = 0b0010010
		self.PO4 = 0b0010011
		self.CC1a = 0b1100000
		self.CC1b = 0b1100001
		self.CC2a = 0b1100010
		self.CC2b = 0b1100011
		self.CC3a = 0b1100100
		self.CC3b = 0b1100101
		self.CC4a = 0b1100110
		self.CC4b = 0b1100111
		self.TE1a = 1101000


	def start(self):
		#creates NodeFGA object and opens connection to FPGA board
		fl.flInitialise(0)
		handle = fl.flOpen(self.vid_pid_did)
		return NodeFPGA(handle)

	def test(self):
		res = []
		#implement tests using memmory map here and append results in correct format to res to be passed to RPI_a_test
		return res
