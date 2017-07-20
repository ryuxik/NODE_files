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
	def __init__(self, old_counter, data):
        self.bounds = self.setup()
        self.old_counter = old_counter
        self.data = data

    def __call__(self):
        """
        Call method for the AlarmRaiser class.

        Returns:
            (list): report of various possble error sources. currents_result is 0 if no errors else list of tuples with failues
                    clock_cycles_since_reset is 0 if no error, int with other number if else.
                    oStatus is tbd
        """

        currents_result = self.checkCurrents()
        clock_cycles_result = self.clockCyclesSinceReset()
        o_status = self.optStatus()
        self.end()
        return [currents_result, clock_cycles_result, o_status]

    def setup(self):
        """
        Uses ConfigParser to set up the bounds dictionary needed to check the current consumption of devices with known safe bounds.
        Also instantiates Tester object.

        Returns:
            (Tester, bounds(dict)): object necessary for other functions and dict with current bounds for each device to be checked
        """

        Config = ConfigParser.ConfigParser()
        Config.read('args.ini')
        bounds = {} #this dictionary holds the locations to be tested along with their respective bounds for acceptable currents
        opts = Config.options('CurrentBounds')
        for o in opts:
        	bounds[o] = Config.get('CurrentBounds', o)
        return bounds

    def optStatus(self):
        """
        Evaluates efficiency of current and temp settings and determines if the optimizer algorithm needs to run.
        """

        #check SER to be below 1 *10^-5
        ser = None
        if ser > 1**(-5):
        	return (True, ser)
        return False

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
        #### LOOK AT DATA SHEETS TO FIGURE OUT CONVERSIONS
    	pass

    def clockCyclesSinceReset(self):
        """
        Reads clock cycles since last reset, used to check if unintentional reset took place
        or if connection to the FPGA board was established if the counter changes over time.

        Returns:
            counter(int): if counter has not changed, indicates error
            (int): 0 if counter changed and became smaller or larger
        """
    	counter = self.data['FRC']
    	if self.old_counter == counter:
    		#'Error: counter since last reset has not changed, possible comm loss'
    		return counter
    	elif old_counter < counter:
    		#'Counter increased to: ', counter, 'delta: ', (counter- old_counter)
    		return 0
    	else:
    		#'Counter decreased to: ', counter, 'delta: ', (counter-old_counter) 
    		return 0

    def readSEM(self):
        """
        
        """
    	flags = self.data['SFL']
    	status = self.data['SST']
    	return (flags, status)

    def checkCurrents(self):
    	"""
    	Checks that the currents are correct and returns report

    	Returns
    		0 if no errors
    		out_of_range(list): list of tuples with (location, current) if they are out of bounds
    	"""
    	##todo, fix this needs current for loc not for a and b split!!
    	out_of_range = [] #array to hold out of range failures
    	for key in self.bounds:
    		d = self.data[key]
    		current = self.code2current(d)
    		if current < self.bounds[key][0] or current > self.bounds[key][1]:
    			out_of_range.append((key, current))
    	if len(out_of_range) > 0:
    		return out_of_range
    	return 0



