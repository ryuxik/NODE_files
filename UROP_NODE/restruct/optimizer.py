#Wavelength Alignment Functions

import fl
import time
import math as m
from datetime import datetime
from mmap import tester

#*assuming fl,handle and fpga objects already created
class Optimizer(object):

    """ Class Initiation """
    def __init__(self, handle, fpga, argList_i, argList_p):
        self.handle = handle
        self.fpga = fpga
        self.mem_map = tester(argList_i, argList_p)

        #Initiate TEC seed laser operating point parameters
        self.temp = 0
        self.current = 0

        #Track adjustments made to previous setpoint and present setpoint
        self.delta_T = 0
        self.delta_C = 0
    """ get functions (check present TEC seed laser operating point) """

    def getTemp(self):
        return self.temp

    def getCurrent(self):
        return self.current

    def getMemMap(self):
        return self.mem_map

    """ set functions (update present TEC seed laser operating point) """

    def setTemp(self,new_temp):
        self.delta_T = new_temp - self.getTemp()
        self.temp = new_temp
        

    def setCurrent(self,new_current):
        self.delta_C = new_current - self.getCurrent()
        self.current = new_current

    """ LaserController functions """
     #TODO: May need to update the SPI channels

    def setLaserCurrent(self, comm_current):
        
        #Current Consumption
        #MSB_channel = 26    #LCCa
        MSB_channel = self.getMemMap().get_addr('LCCa')
        #LSB_channel = 27    #LCCb
        LSB_channel = self.getMemMap().get_addr('LCCb')

        #Convert commanded current to bytes
        code = comm_current/(4.096*1.1*((1/6.81)+(1/16500)))*4096
        first_byte, second_byte = self.code2bytes(code)

        fl.flWriteChannel(self.handle,MSB_channel,first_byte)      #writes bytes to channel
        fl.flWriteChannel(self.handle,LSB_channel,second_byte)

    def setLaserTemp(self, comm_temp):
        
        #Temp Set Point
        #MSB_channel = 23    #LTSa
        MSB_channel = self.getMemMap().get_addr('LTSa')  
        #LSB_channel = 24    #LTSb
        LSB_channel = self.getMemMap().get_addr('LTSb')

        #TODO Constants are estimated; may need to verify with vendor
        R_known = 10000
        Vcc = 0.8
        B = 3900
        R_0 = 10000
        T_0 = 25 
        
        #converts input/commanded temp (comm_temp) to voltage
        V_set = Vcc/(((m.exp(B/comm_temp)*(R_0 * m.exp(-B/T_0)))/R_known)+1)
        V_code = self.voltage2code(V_set) #convert voltage to code
        fb, sb = self.code2byte(V_code) #convert code to bytes
        
        fl.flWriteChannel(self.handle,MSB_channel, fb)
        fl.flWriteChannel(self.handle,LSB_channel, sb)


    def getLaserCurrent(self):

        #Current Consumption 3
        #MSB_channel = 100   #CC3a
        MSB_channel = self.getMemMap().get_addr('CC3a')
        #LSB_channel = 101   #CC3b
        LSB_channel = self.getMemMap().get_addr('CC3b')

        rxm = fl.flReadChannel(self.handle, MSB_channel)
        rxl = fl.flReadChannel(self.handle, LSB_channel)

        #converts the bytes read to a current value
        return (rxm*256 + rxl)/4096 * (4.096*1.1*((1/6.81)+(1/16500)))


    def getLaserTemp(self):

        #Measured Temp
        #MSB_channel = 116   #LTMa
        MSB_channel = self.getMemMap().get_addr('LTMa')

        #LSB_channel = 117   #LTMb
        LSB_channel = self.getMemMap().get_addr('LTMb')
        
        rxm = fl.flReadChannel(self.handle,MSB_channel)
        rxl = fl.flReadChannel(self.handle,LSB_channel)

        code_meas = rxm*256 + rxl           #byte to code
        V_meas = self.code2voltage(code_meas)

        #Converts voltage to temperature
        R_t = R_known * (Vcc/V_meas - 1)
        T = B/m.log(R_t/R_0 * m.exp(-B/T_0))

        return T
    
    def code2byte(self, code):
        fb = code/256   #first byte, second byte
        sb = code%256
        return fb, sb

    def voltage2code(self, v):
        max_code = 2**12 #assuming 12-bit ADC
        V_cc = 3.3  #assuming 3.3V source
        return v*(max_code/3.3)

    def code2voltage(self, c):
        max_code = 2**12 #assuming 12-bit ADC
        V_cc = 3.3 #assuming 3.3V source
        return c*(V_cc/max_code)


    """ Functions for alignment algorithm """

    # Scan mode assumes no known operating setpoint and outputs an operating point using hill-climbing search for temp and bias_current
    def scan_mode(self, obslength):
        #obslength from float(argList.peak) in Ryan's Code

        ###scan mode###
		current = 125

        self.setLaserCurrent(current)  

		time.sleep(2)
        #adjusts current if laser current is more than +/- 0.1 from current, continues until current settles w/o changing after sleep
		while not (current - 0.1 <= round(self.getLaserCurrent(),1) <= current + 0.1):

            self.setLaserCurrent(current)                                                  
			time.sleep(1)

		temp = 38

		self.setLaserTemp(temp)
		time.sleep(2)
        #waits until laser temperature is equal to temp, continues until temp settles w/o changing after sleep
		while not(m.floor(self.getLaserTemp()) == round(temp,1)):
			time.sleep(1)

		###get temp/current again since commanded current/temp may not be 100% accurate###
		temp = self.getLaserTemp()
		current = self.getLaserCurrent()
		print("New temperature: %f, new current: %f"%(temp, current))
		print("Measuring slot error rate...")

		cycles,errors,ones,ser = self.fpga.measureSER(obslength=obslength)
		#f.write(str(datetime.now())+','+str(temp)+','+str(current)+','+str(ser)+'\n')
		print(" cycles = 0x%-12X"%(cycles))
		print(" errors = 0x%-12X"%(errors))

        #M is not defined here, it is calculated in the main control
        #not sure if we need this print statement anyway
		#print(" ones   = 0x%-12X target=0x%-12X"%(ones,cycles/M))
		print(" SlotER = %e"%(ser))

		print('Begin Algorithm')
		start_time = datetime.now()           
		curr_time = datetime.now()
		ntemp = temp
		ncurrent = current
		while (True):
			cycles,errors,ones,ser = self.fpga.measureSER(obslength=obslength)

			tser = ser #keep track of last temperature_ser to differentiate from current_ser
			curr_time = datetime.now()
			###Vary temperature by smallest resolution zzz (TBD)###
			zzz = 0.1
			ntemp = ntemp + zzz
			self.setLaserTemp(ntemp)
			time.sleep(2)

			ncycles, nerrors, nones, nser = self.fpga.measureSER(obslength=obslength)
			#f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
			print("New temperature: %f, nser: %e" %(ntemp, nser))
			while (nser < tser)  and nser != 0:
    			#safety check 
    			if (ntemp >= 50):                    
    				print("temp exceeded")
    				break
    			tser = nser
    			ntemp = ntemp + zzz

    			self.setLaserTemp(ntemp)
    			time.sleep(5)
    			ncycles, nerrors, nones, nser = self.fpga.measureSER(obslength=obslength)
    			print("New temperature: %f, nser: %e" %(ntemp,nser))
    			#f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
	   
			###increasing temperature results in worse ser; go in reverse direction###
			if (nser > (tser+1*10**(m.floor(m.log10(abs(tser)))))) and nser != 0 and (tser<1e-2):
			tser = nser
			ntemp = ntemp - zzz

			self.setLaserTemp(ntemp)
			time.sleep(5)
			ncycles, nerrors, nones, nser = self.fpga.measureSER(obslength=obslength)
			#f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
			print("New temperature %f, nser: %e" %(ntemp, nser))
			while (nser <= tser) and ser != 0:
				tser = nser
				ntemp = ntemp - zzz

				self.setLaserTemp(ntemp)
				time.sleep(5)
				ncycles, nerrors, nones, nser = self.fpga.measureSER(obslength=obslength)
				#f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
				print("New temperature: %f, nser: %e" %(ntemp,nser))
			
			tser = nser #update tser before adjusting current
			print("Current temperature: %f, current ser: %e" %(ntemp,tser))
			#f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(ser)+'\n')           
		   
			###Vary Current by smallest resolution (TBD) ccc  (only start after SER is above noise floor)###
			if (tser<1e-2):
			cser = tser #keep track of current_ser to differentiate from temperature_ser
			ccc = 0.1
			ncurrent = ncurrent + ccc

			self.setLaserCurrent(ncurrent)
			time.sleep(2)
			ncycles, nerrors, nones, nser = self.fpga.measureSER(obslength=obslength)
			print("New current: %f, nser: %e" %(ncurrent, nser))
			#f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')

			
			while (nser < cser) and nser != 0 :
				#safety check
				if (ncurrent >= 138):
					print("curr exceeded")
					break
				cser = nser
				ncurrent = ncurrent + ccc

				self.setLaserCurrent(ncurrent)
				time.sleep(2)
				ncycles, nerrors, nones, nser = self.fpga.measureSER(obslength=obslength)
				print("New current: %f, nser: %e" %(ncurrent,nser))
				#f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
				

			###increasing current results in worst ser; go in reverse direction###
			if (nser > (cser))  and nser != 0:
				cser = nser
				ncurrent = ncurrent - ccc

				self.setLaserCurrent(ncurrent)
				time.sleep(2)
				ncycles,nerrors,nones,nser = self.fpga.measureSER(obslength=obslength)
				#f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
				print("New current: %f, nser: %e" %(ncurrent,nser))
				while (nser < cser) and nser!= 0:
					cser = nser
					ncurrent = ncurrent - ccc

					self.setLaserCurrent(ncurrent)
					time.sleep(2)
					ncycles, nerrors, nones, nser = self.fpga.measureSER(obslength=obslength)
					f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
					#print("New current: %f, nser: %e" %(ncurrent,nser))

			print("Current curr: %f" %(ncurrent))

			#f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')

			###If SER reaches minimum, peak power achieved###
			if (nser <= 1e-5):
			print("Minimum SER reached, algorithm ending; ntemp: %f; ncurrent: %f"%(ntemp,ncurrent))
			###save temp,current setpoint values###
			self.setTemp(ntemp)
			self.setCurrent(ncurrent)
			#f.write(str(ntemp)+','+str(ncurrent)+'\n')
			break
			
    # Dither mode assumes operating point determined (using scan_mode) and makes minor adjustments for  bias_current only
    def dither_mode(self, obslength):
        ###dither mode###
        current = self.getLaserCurrent()

        temp = self.getLaserTemp()

        print("Present temperature: %f, Present current: %f"%(temp, current))
        print("Measuring slot error rate...")
        cycles,errors,ones,ser = self.fpga.measureSER(obslength=obslength)
        #f.write(str(datetime.now())+','+str(temp)+','+str(current)+','+str(ser)+'\n')
        print(" cycles = 0x%-12X"%(cycles))
        print(" errors = 0x%-12X"%(errors))
        print(" ones   = 0x%-12X target=0x%-12X"%(ones,cycles/M))
        print(" SlotER = %e"%(ser))

        print('Begin Algorithm')
        start_time = datetime.now()           
        curr_time = datetime.now()
        ntemp = temp
        ncurrent = current

        while (True):

            cycles,errors,ones,ser = self.fpga.measureSER(obslength=obslength)

            ###Vary Current by smallest resolution ccc (only start after SER is above noise floor)###
            
            cser = ser 
            ccc = 0.1
            ncurrent = ncurrent + ccc

            self.setLaserCurrent(ncurrent)
            time.sleep(2)
            ncycles, nerrors, nones, nser = self.fpga.measureSER(obslength=obslength)
            print("New current: %f, nser: %e" %(ncurrent, nser))
            #f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')

            if (nser < cser) and nser != 0:
                while (nser < cser) and nser != 0 :
                    #safety check
                    if (ncurrent >= 138):
                        print("curr exceeded")
                        break
                    cser = nser
                    ncurrent = ncurrent + ccc

                    self.setLaserCurrent(ncurrent)
                    time.sleep(2)
                    ncycles, nerrors, nones, nser = self.fpga.measureSER(obslength=obslength)
                    print("New current: %f, nser: %e" %(ncurrent,nser))
                    #f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')

            elif (nser == cser):
                ncurrent = ncurrent - ccc

                self.setLaserCurrent(ncurrent)
                time.sleep(2)
                ncycles,nerrors,nones,nser = self.fpga.measureSER(obslength=obslength)
                #f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                print("New current: %f, nser: %e" %(ncurrent, nser))
            
            ###increasing current results in worst ser###
            elif (nser > (cser))  and nser != 0:
                cser = nser
                ncurrent = ncurrent - ccc

                self.setLaserCurrent(ncurrent)
                time.sleep(2)
                ncycles,nerrors,nones,nser = self.fpga.measureSER(obslength=obslength)
                #f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                print("New current: %f, nser: %e" %(ncurrent,nser))
                while (nser < cser) and nser!= 0:
                    cser = nser
                    ncurrent = ncurrent - ccc

                    self.setLaserCurrent(ncurrent)
                    time.sleep(2)
                    ncycles, nerrors, nones, nser = self.fpga.measureSER(obslength=obslength)
                    #f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                    print("New current: %f, nser: %e" %(ncurrent,nser))

            print("Current curr: %f" %(ncurrent))


        #f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
        ###If SER reaches minimum, peak power achieved###
        if (nser <= ser):
            print("Minimum SER reached, algorithm ending; ntemp: %f; ncurrent: %f"%(ntemp,ncurrent))
            #save temp,current setpoint values
            self.setTemp(ntemp)
            self.setCurrent(ncurrent)
            #f.write(str(ntemp)+','+str(ncurrent)+'\n')
            break
            

    # TEC power consumption optimization feature (require ambient temperature reading from TOSA RTD)
    def power_opt(self,T_amb):
        
        #Seed laser model (output wavelength dependencies)
        dw_dt = 0.088 #change_in_ wavelength(nm)/change_in_temp(C)
        dw_dc = 0.0036 #change_in_wavelength(nm)/change_in_current(mA)

        
        #Seed laser model (power consumption)
        
        """ P_temp """
        k = 0
        dT = T_amb - self.getTemp() #T_amb-T_set
        if dT > 0: #heating
            k = 0.2/(15**2)
        elif dT < 0: #cooling
            k = 0.4/((-20)**2)
        P_temp = k*(dT)**2 #model derived from Ryan Kingsbury's thesis pg.79
        
        """ Normalized power consumption for bias consumption (per degree C) """
        #We calculate the number of mA needed to produce the same wavelength shift for 1 degree C
        P_curr_norm = 3.3 * ((0.088/0.0036)/1000) * dT #P=VI with V from ADN8810 datasheet


        #Calculate total change in wavelength of new set point
        dw = abs(self.delta_T)*dw_dt + abs(self.delta_C)*dw_dc

        #Optimize
        if P_temp > P_curr_norm: #Adjustments in mA will be more power efficient
            ntemp = T_amb - (P_curr_norm/k)**(0.5) #Calculate T_set at intersection (from eq k*T_amb-T_set)^2 = P_curr_norm)
            dw_remaining = (ntemp - (self.getTemp()-self.delta_T))*dw_dt #Calculate wavelength shift from new temp
            ncurr = self.getCurrent() + round(dw_remaining/dw_dc,2) #Finish remaining wavelength shift using bias current (since it is more efficient)
            #Update operating points
            self.setTemp(ntemp)
            self.setCurrent(ncurr)