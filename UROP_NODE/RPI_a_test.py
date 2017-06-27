"""
@Author: Santiago Munoz
@Date: 6/13/17
	
	Acceptance test for the Rasperry Pi Baseboard with the Modulator, Camera, and Bus.
"""
## Must fix code to work with new connection class
import test.busComm as comm
import test.fpga_link_test as flink
import test.mmap_test.py as mmap
from restruct.node import NodeFPGA 

if __name__ == "__main__":
	testsPassed = False
	progConfig = '' #replace with FPGA config file
	fpga_old_vid_pid = '1:0:1' # replace with proper vendor and product id and device id of FPGA board
	new_vid_pid = ''
	debug_level = 0 #replace with desired debug level for fl API
	
	#pl Bus info required for usb connection
	plBus_vid = ''
	plBus_pid = ''
	plBus_packet_size = ''
	plBus_timeout = ''
	plBus_master_sendTest = ''
	plBus_master_expectTest = ''
	plBus_slave_sendTest = ''
	plBus_slave_expectTest = ''
	
	#camera info required for usb connection
	camera_vid = ''
	camera_pid = ''
	camera_packet_size = ''
	camera_timeout = ''
	camera_sendTest = ''
	camera_expectTest = ''

	#switch1 info required for usb connection, may replace later with different connection type
	switch1_vid = ''
	switch1_pid = ''
	switch1_packet_size = ''
	switch1_timeout = ''

	#switch2 info required for usb connection, may replace later with different connection type
	switch2_vid = ''
	switch2_pid = ''
	switch2_packet_size = ''
	switch2_timeout = ''

	results = [] #array containing test results

	#Making instances of necessary connections for test
	
	##need to find out what type of usb transfer to use for each of these
	plBusMaster = comm.connection(plBus_vid,plBus_pid,plBus_packet_size,plBus_timeout,True)
	camera = comm.connection(camera_vid,camera_pid,camera_packet_size,camera_timeout)
	switch1 = comm.connection(switch1_vid, switch1_pid, switch1_packet_size, switch1_timeout)
	switch2 = comm.connection(switch2_vid, switch2_pid, switch2_packet_size, switch2_timeout)
	
	mem = mmap.tester(fpga_old_vid_pid, fpga_new_vid_pid)

	init_fpga_board_tester = flink.board(fpga_old_vid_pid_did, debug_level, None)

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
		results.extend(mem.test(progConfig))
	except:
		results.append('F','Memmory map command testing to FPGA test failed to run.')

	#Testing switch of bus to slave
	try:
		#implement a slave test here!!
		pass
		#do something to switch both 1 and 2 to set plBus as slave
	except:
		results.append('F','Switch of bus to slave failed')
		
	#Testing connection to bus as slave
	try:
		plBusSlave = comm.connection(plBus_vid,plBus_pid,plBus_packet_size,plBus_timeout)
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