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
        ##FIX
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
    		code(tuple): data received from channel
    	Returns
    		current(double): current derived from code
    	"""
    	##need to implement converter from data read to current
    	##something like this
        return (code[0]*256 + code[1])/4096 * (4.096*1.1*((1/6.81)+(1/16500))) #not sure if this works for all locs
        #### LOOK AT DATA SHEETS TO FIGURE OUT CONVERSIONS

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
        to_check = [('CC1a', 'CC1b'), ('CC2a', 'CC2b'), ('CC3a', 'CC3b'), ('CC4a', 'CC4b')]
        currents = []
    	out_of_range = [] #array to hold out of range failures
    	
        #get currents at locations
        for pair in to_check:
    		currents.append(self.code2current(self.data[pair[0]], self.data[pair[1]]))
    	
        #check if currents in bounds
        if not self.bounds['LOC1'] < currents[0] < self.bounds['LOC1']:
            out_of_range.append('LOC1', currents[0])
        if if not self.bounds['LOC2'] < currents[1] < self.bounds['LOC2']:
            out_of_range.append('LOC2', currents[1])
        if not self.bounds['LOC3'] < currents[2] < self.bounds['LOC3']:
            out_of_range.append('LOC3', currents[2])
        if not self.bounds['LOC4'] < currents[3] < self.bounds['LOC4']:
            out_of_range.append('LOC4', currents[3])
        
        #return errors if they exist
        if len(out_of_range) > 0:
            return out_of_range
    	return 0



