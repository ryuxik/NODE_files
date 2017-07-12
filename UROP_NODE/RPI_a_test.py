"""
@Author: Santiago Munoz
@Date: 6/13/17
	
	Acceptance test for the Rasperry Pi Baseboard with the Modulator, Camera, and Bus.
"""
## Need to plug into pi and devices to find out info and code it in
import busComm as comm
import test.fpga_link_test as flink
import mmap_test.py as mmap
from restruct.node import NodeFPGA
import rpiControls.pinController as pinC
from constants import ALL_C

if __name__ == "__main__":
	testsPassed = False
	
	## find out what type of transfer each connection is (control, isochronous, interrupt, or bulk)
	#pl Bus info required for usb connection
	
	plBus_master_sendTest = ''
	plBus_master_expectTest = ''
	plBus_slave_sendTest = ''
	plBus_slave_expectTest = ''
	
	
	#camera info required for usb connection
	
	camera_sendTest = ''
	camera_expectTest = ''
	
	results = [] #array containing test results

	#Making instances of necessary connections for test
	
	##need to find out what type of usb transfer to use for each of these
	plBusMaster = comm.Connection(ALL_C['plBus_vid'],ALL_C['plBus_pid'],ALL_C['plBus_packet_size'],ALL_C['plBus_timeout'], ALL_C['plBus_wendpoint'], ALL_C['plBus_rendpoint'], True)
	camera = comm.Connection(ALL_C['camera_vid'],ALL_C['camera_pid'],ALL_C['camera_packet_size'],ALL_C['camera_timeout'], ALL_C['camera_wendpoint'], ALL_C['camera_rendpoint'])
	
	mem = mmap.Tester(ALL_C['fpga_old_vid_pid'], ALL_C['fpga_new_vid_pid'])

	init_fpga_board_tester = flink.Board(ALL_C['fpga_old_vid_pid'], ALL_C['debug_level'], None)

	#Testing intial connection to bus
	try:
		results.append(plBusMaster.testConnection(plBus_master_sendTest,plBus_master_expectTest))
	except:
		results.append('F','Initial connection to bus failed')

	#Testing connection to camera
	try:
		results.append(camera.testConnection(camera_sendTest, camera_expectTest))
	except:
		results.append('F','Connection to camera failed')

	#Testing connection to FPGA board
	try:
		results.extend(init_fpga_board_tester.init_com_test()) #run tests and return list of to extend results report
	except:
		results.append('F','FPGA inital connection test failed to run.')
	
	#Make tests using memmory map here!!
	try:
		results.extend(mem.test(ALL_C['progConfig']))
	except:
		results.append('F','Memmory map command testing to FPGA test failed to run.')

	#Testing switch of bus to slave
	try:
		#implement a slave test here!!
		results.append(pinC.main())
		#do something to switch both 1 and 2 to set plBus as slave
	except:
		results.append('F','Switch of bus to slave failed')
		
	#Testing connection to bus as slave
	try:
		plBusSlave = comm.Connection(ALL_C['plBus_vid'],ALL_C['plBus_pid'],ALL_C['plBus_packet_size'],ALL_C['plBus_timeout'], ALL_C['plBus_wendpoint'], ALL_C['plBus_rendpoint'])
		results.append(plBusSlave.testConnection(plBus_slave_sendTest, plBus_slave_expectTest))
	except:
		results.append('F','Connection to bus as slave failed')

	#print(results) #see results of tests

	#Check for F at as the first element of every statement, if so, add it to list of failures
	failures = [statement[1:] for statement in results if statement[0] == 'F']

	#Check if all tests have passed
	if len(failures) == 0:
		testsPassed = True

	#store results in text file
	f = open('results','w')
	if testsPassed:
		f.write('All tests passed')
	else:
		for r in failures:
			f.write(r)
	f.close()