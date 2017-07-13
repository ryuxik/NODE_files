import mmap_test.py as mmap
import ConfigParser
"""
This is to test the currents of devices during the alarms section of the cotrol code.
It reports errors when devices are not cosuming the current they should be consuming.
"""


class AlarmRaiser(object):
	"""
    This class holds the necessary methods to raise alarms during the alarms section of the control code.
    It checks for correct current consumption, correct clock cycle count, and if optimization is needed.
    """
	def __init__(self, old_vid_pid, new_vid_pid):
        self.bounds = self.setupBounds() #bounds dictionary
        self.m = self.start(old_vid_pid, new_vid_pid) #Tester object

    def setupBounds(self):
        """
        Uses ConfigParser to set up the bounds dictionary needed to check the current consumption of devices with known safe bounds

        Returns:
            bounds(dict): dict with current bounds for each device to be checked
        """
        Config = ConfigParser.ConfigParser()
        Config.read('args.ini')
        bounds = {} #this dictionary holds the locations to be tested along with their respective bounds for acceptable currents
        opts = Config.options('CurrentBounds')
        for o in opts:
        	bounds[o] = Config.getint('CurrentBounds', o)
        return bounds

    def opt_status(self):
        """
        Evaluates efficiency of current and temp settings and determines if the optimizer algorithm needs to run.
        """
        pass

    def code2current(self, code):
    	"""
    	Takes data received from a channel and converts it to a current

    	Args:
    		code(): data received from channel
    	Returns
    		current(double): current derived from code
    	"""
    	##need to implement converter from data read to current
    	##something like this
    	# def code2byte(code):
     #    	fb = code/256
     #    	sb = code%256
     #    	return fb, sb
    	# def code2voltage(c):
     #    	max_code = 2**12 #assuming 12-bit ADC
     #    	V_cc = 3.3 #assuming 3.3V source
     #    	return c*(V_cc/max_code)
    	pass

    def start(self, old_vid_pid, new_vid_pid):
    	return mmap.Tester(old_vid_pid, new_vid_pid) #initialize memmory map

    def end(self):
    	self.m.end(self.m.fpga) #closes connection to the FPGA that was opened by instantiating the Tester object

    def clock_cycles_since_reset(self, old_counter):
    	counter = self.m.read(self.m.fpga, self.m.get_addr('FRC'))
    	if old_counter == counter:
    		#'Error: counter since last reset has not changed, possible comm loss'
    		return counter
    	elif old_counter < counter:
    		#'Counter increased to: ', counter, 'delta: ', (counter- old_counter)
    		return 0
    	else:
    		#'Counter decreased to: ', counter, 'delta: ', (counter-old_counter) 
    		return 0

    def read_SEM(self):
    	flags = self.m.read(self.m.fpga, self.m.get_addr('SFL'))
    	status = self.m.read(self.m.fpga, self.m.get_addr('SST'))
    	return (flags, status)

    def check_currents(self):
    	"""
    	Checks that the currents are correct and returns report

    	Args:
    		old_vid_pid(): vendor and product id
    		new_vid_pid(): vendor and product id
    	Returns
    		0 if no errors
    		out_of_range(list): list of tuples with (location, current) if they are out of bounds
    	"""
    	
    	out_of_range = [] #array to hold out of range failures
    	for key in self.bounds:
    		data = self.m.read(self.m.fpga, self.m.get_addr(key))
    		current = self.code2current(data)
    		if current < self.bounds[key][0] or current > self.bounds[key][1]:
    			out_of_range.append((key, current))
    	if len(out_of_range) > 0:
    		return out_of_range
    	return 0



