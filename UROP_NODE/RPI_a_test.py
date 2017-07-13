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
import ConfigParser

if __name__ == "__main__":
	testsPassed = False
	Config = ConfigParser.ConfigParser()
    Config.read('args.ini')
    configurations = {} #this dictionary holds the configuration files
    commInfo = {} #this dictionary holds the info necessary for communication with devices
    comms = Config.options('ConnectionInfo')
    confs = Config.options('ConfigurationFiles')
    for con in confs:
    	configurations[con] = Config.get('ConfigurationFiles', con)
    for com in comms:
    	commInfo[com] = Config.get('ConnectionInfo', com)
	
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
	plBusMaster = comm.Connection(
                                    commInfo['plBus_vid'], commInfo['plBus_pid'], commInfo['plBus_packet_size'],
                                    commInfo['plBus_timeout'], commInfo['plBus_wendpoint'], commInfo['plBus_rendpoint'], True)
    camera = comm.Connection(
                                commInfo['camera_vid'], commInfo['camera_pid'], commInfo['camera_packet_size'],
                                commInfo['camera_timeout'], commInfo['camera_wendpoint'], commInfo['camera_rendpoint'])
	mem = mmap.Tester(commInfo['fpga_old_vid_pid'], commInfo['fpga_new_vid_pid'])
	init_fpga_board_tester = flink.Board(commInfo['fpga_old_vid_pid'], commInfo['debug_level'], None)
	
    try:   #Testing intial connection to bus
		results.append(plBusMaster.testConnection(plBus_master_sendTest,plBus_master_expectTest))
	except:
		results.append('F','Initial connection to bus failed')
	try:   #Testing connection to camera
		results.append(camera.testConnection(camera_sendTest, camera_expectTest))
	except:
		results.append('F','Connection to camera failed')
	try:   #Testing connection to FPGA board
		results.extend(init_fpga_board_tester.init_com_test()) #run tests and return list of to extend results report
	except:
		results.append('F','FPGA inital connection test failed to run.')
	try:   #Make tests using memmory map here!!
		results.extend(mem.test(configurations['progConfig']))
	except:
		results.append('F','Memmory map command testing to FPGA test failed to run.')
	try:   #Testing switch of bus to slave
		#implement a slave test here!!
		results.append(pinC.main())
		#do something to switch both 1 and 2 to set plBus as slave
	except:
		results.append('F','Switch of bus to slave failed')
	try:   #Testing connection to bus as slave
		plBusSlave = comm.Connection(
                                        commInfo['plBus_vid'], commInfo['plBus_pid'], commInfo['plBus_packet_size'],
                                        commInfo['plBus_timeout'], commInfo['plBus_wendpoint'], commInfo['plBus_rendpoint'])
		results.append(plBusSlave.testConnection(plBus_slave_sendTest, plBus_slave_expectTest))
	except:
		results.append('F','Connection to bus as slave failed')
	#print(results) #see results of tests

	failures = [statement[1:] for statement in results if statement[0] == 'F']    #Check for F at as the first element of every statement, if so, add it to list of failures
	if len(failures) == 0:    #Check if all tests have passed
		testsPassed = True

	#store results in text file
	f = open('results','w')
	if testsPassed:
		f.write('All tests passed')
	else:
		for r in failures:
			f.write(r)
	f.close()