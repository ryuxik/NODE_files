"""
NODE FPGA Commander Copyright (C) 2015 Ryan Kingsbury
-Updated and restructured by Santiago Munoz, 2017
"""
import fl
import argparse
import time
import struct
import csv
from datetime import datetime
from node import NodeFPGA
import sys
import math as m
from bench import LaserController

#DEBUG = False

# FPGA image, must update with new directory/ host on rpi cm3!!!!
#FPGA_IMAGE = "/home/kingryan/Dropbox/grad_school/fpga/makestuff/hdlmake/apps/roamingryan/swled/bist/vhdl/top_level.xsvf"

def main():
    """
    Main control function, gets necessary arguments and prints status relevant reports.
    """

    argList = get_args()
    print (argList)
    handle = fl.FLHandle()
    try:
        fl.flInitialise(0)
        vp = argList.v[0]
        print("Attempting to open connection to FPGALink device {}...".format(vp))
        try:
            handle = fl.flOpen(vp)
        except fl.FLException as ex:
            handle = ids(vp, argList)
        if argList.c:
            isNeroCapable, isCommCapable = conduit_selection(int(argList.c[0]))
        else:
            isNeroCapable, isCommCapable = conduit_selection()
        
        jtag_chain(isNeroCapable, argList, vp, handle)
        
        configure(argList, isNeroCapable, handle, vp)
        
        if argList.f and not isCommCapable:
            raise fl.FLException("Data file load requested but device at {} does not support CommFPGA".format(vp))

        if isCommCapable and fl.flIsFPGARunning(handle):

            fpga = NodeFPGA(handle)

            # define channels
            writechannel = 0x02
            statuschannel = 0x05
            resetchannel = 0x08

            if argList.ppm:
                M = int(eval(argList.ppm[0]))
                print ("Setting PPM order to",M)
                fpga.setPPM_M(M)

            writedelay,num_bytes,trackingbyte = fpga.setModulatorParams(M)

            if not argList.f:
                fpga.setTrackingMode(writechannel,trackingbyte,M)

            if argList.txdel:
                delay = int(eval(argList.txdel[0]))
                print ("Setting transmitter loopback delay to %i (0x%X)"%(delay,delay))
                fpga.setTXdelay(delay)

            if argList.dac:
                dacval = int(eval(argList.dac[0]))
                print ("Setting DAC value to %i (0x%X)"%(dacval,dacval))
                fpga.writeDAC(dacval)

            if argList.prbs:
                print ("Enabling PRBS")
                fpga.usePRBS()

            else:
                print ("Disabling PRBS")
                fpga.usePRBS(False)

            if argList.peak:
                obslength = float(argList.peak)
                print ("Measuring peak power...")
                peakDAC = fpga.binSearchPeak(M,target=1.0/M,obslength=obslength)
                print ("  DAC = %i"%peakDAC)

            if argList.ser:
                obslength = float(argList.ser)
                print ("Measuring slot error rate...")
                cycles,errors,ones,ser = fpga.measureSER(obslength=obslength)
                print (" cycles = 0x%-12X"%(cycles))
                print (" errors = 0x%-12X"%(errors))
                print (" ones   = 0x%-12X target=0x%-12X"%(ones,cycles/M))
                print (" SlotER = %e"%(ser))
        
            data_to_write(argList, fpga, writechannel, resetchannel, statuschannel, writedelay, vp, N, num_bytes)

            #alg testing goes here, but alg is not up to date!!
            opt_alg(argList, fpga)
            
    except fl.FLException as ex:
        print(ex)
    finally:
        fl.flClose(handle)

def readFile(fileName):
    """
    File-reader which yields chunks of data

    Args:
        fileName(string): name of file to read
    """    

    with open(fileName, "rb") as f:
        while True:
            chunk = f.read(32768)
            if chunk:
                yield chunk
            else:
                break

def get_args():
     """
    Gets neccessary args to communicate and program FPGA board.
    ## Maybe replace so that it gets these arguments from the proper place using modes

    Returns:
        argList(namespace): populated namespace object
    """
    parser = argparse.ArgumentParser(description='Load FX2LP firmware, load the FPGA, interact with the FPGA.')
    parser.add_argument('-i', action="store", nargs=1, metavar="<VID:PID>", help="vendor ID and product ID (e.g 1443:0007)")
    parser.add_argument('-v', action="store", nargs=1, required=True, metavar="<VID:PID>", help="VID, PID and opt. dev ID (e.g 1D50:602B:0001)")
    #parser.add_argument('-d', action="store", nargs=1, metavar="<port+>", help="read/write digital ports (e.g B13+,C1-,B2?)")
    parser.add_argument('-q', action="store", nargs=1, metavar="<jtagPorts>", help="query the JTAG chain")
    parser.add_argument('-p', action="store", nargs=1, metavar="<config>", help="program a device")
    parser.add_argument('-c', action="store", nargs=1, metavar="<conduit>", help="which comm conduit to choose (default 0x01)")
    parser.add_argument('-f', action="store", nargs=1, metavar="<dataFile>", help="binary data to write to channel 0")
    parser.add_argument('-N', action="store", nargs=1, metavar="numwrites", help="Number of times to write file to FPGA")
    parser.add_argument('--ppm', action="store", nargs=1, metavar="<M>", help="PPM order")
    parser.add_argument('--txdel', action="store", nargs=1, metavar="<delay>", help="TX loopback delay (in clock cycles)")
    parser.add_argument('--dac', action="store", nargs=1, metavar="<counts>", help="DAC setting")
    parser.add_argument('--prbs', action="store", nargs='?',const=True, metavar="<prbs>", help="Use PRBS")
    parser.add_argument('--ser', action="store", nargs='?',const='1', metavar="<dwell>", help="perform slot error rate measurement")
    parser.add_argument('--peak', action="store", nargs='?',const='0.1', metavar="<dwell>", help="peak power measurement, binary search for DAC value")
    argList = parser.parse_args()
    return argList

def ids(vp, argList):
     """
    Handles opening connection to FPGA board when flOpen fails initially. Also loads standard firmware using device id

    Args:
        vp(): vendor ID and product ID
        argList(namespace): populated namespace object

    Returns:
        An opaque reference to an internal structure representing the connection.
        This must be freed at some later time by a call to \c flClose(), or a resource-leak will ensue.

    """
    if argList.i:
        ivp = argList.i[0]
        print("Loading firmware into {}...".format(ivp))
        fl.flLoadStandardFirmware(ivp, vp)
        # Long delay for renumeration
        # TODO: fix this hack.  The timeout value specified in flAwaitDevice() below doesn't seem to work
        time.sleep(3)
        print("Awaiting renumeration...")
        if ( not fl.flAwaitDevice(vp, 10000) ):
            raise fl.FLException("FPGALink device did not renumerate properly as {}".format(vp))
        print("Attempting to open connection to FPGALink device {} again...".format(vp))
        return fl.flOpen(vp)
    else:
        raise fl.FLException("Could not open FPGALink device at {} and no initial VID:PID was supplied".format(vp))

def conduit_selection(argList_c=1):
    """
    Selects conduit and checks if the FPGA board is nero capable and capable of communication.

    Args:
        argList_c(int): comm conduit to chose
    Returns:
        (tuple): booleans indicating if device is nero capable and comm capable
    """
    isNeroCapable = fl.flIsNeroCapable(handle)
    isCommCapable = fl.flIsCommCapable(handle, conduit)
    fl.flSelectConduit(handle, conduit)
    return (isNeroCapable, isCommCapable)

def jtag_chain(isNeroCapable, argList, vp, handle):
    """
    Tests the JTAG chain.

    Args:
        isNeroCapable(boolean): indicated if device is nero capable
        argList(namespace): populated namespaced object with necessary args
        vp(): vendor and product ID
        handle: An opaque reference to an internal structure representing the connection.
    """
    if argList.q:
        if isNeroCapable:
            chain = fl.jtagScanChain(handle, argList.q[0])
            if len(chain) > 0:
                print("The FPGALink device at {} scanned its JTAG chain, yielding:".format(vp))
                for idCode in chain:
                    print("  0x{:08X}".format(idCode))
            else:
                print("The FPGALink device at {} scanned its JTAG chain but did not find any attached devices".format(vp))
        else:
            raise fl.FLException("JTAG chain scan requested but FPGALink device at {} does not support NeroJTAG".format(vp))

def configure(argList, isNeroCapable, handle, vp):
    """
    Configures FPGA board with selected program.

    Args:
        argList(namespace): populated namespaced object with necessary args
        isNeroCapable(boolean): indicated if device is nero capable
        handle: An opaque reference to an internal structure representing the connection.
        vp(): vendor and product ID
    """
    if argList.p:
        progConfig = argList.p[0]
        print("Programming device with config {}...".format(progConfig))
        if isNeroCapable:
            fl.flProgram(handle, progConfig)
        else:
            raise fl.FLException("Device program requested but device at {} does not support NeroProg".format(vp))

def opt_alg(argList, fpga):
    """
    Optimizing algorithm, needs to be updated to use optimizer.py file. Has two modes.

    Args:
        argList(namespace): populated namespace object
        fpga(NodeFPGA): object representing fpga board
    """
    if argList.ser:
        f = open('ppm128_ser_dither.csv', 'w')
        obslength = float(argList.ser)
        gpib_port = "/dev/ttyUSB0"
        controller = LaserController(gpib_port,20)
        print ('Laser output Mode: ' + str(controller.getLaserOutput()))
        print ('TEC output Mode: ' + str(controller.getTECOutput()))
                 
        #enable output modes
        controller.setLaserOutput(1);
        time.sleep(5)
        controller.setTECOutput(1);
        time.sleep(5)

        mode = 1 #0 for scan, 1 for dither

        if (mode == 0):
            #scan mode
            current = 125
            controller.setLaserCurrent(current)
            time.sleep(2)
            while not (current - 0.1 <= round(controller.getLaserCurrent(),1) <= current + 0.1):
                controller.setLaserCurrent(current)
                time.sleep(1)
            
            
            temp = 38
            controller.setLaserTemp(temp)
            time.sleep(2)
            while not(m.floor(controller.getLaserTemp()) == round(temp,1)):
                time.sleep(1)

            #get temp/current again since commanded current/temp may not be 100% accurate
            temp = controller.getLaserTemp()
            current = controller.getLaserCurrent()
            print ("New temperature: %f, new current: %f"%(temp, current))
            print ("Measuring slot error rate...")
            cycles,errors,ones,ser = fpga.measureSER(obslength=obslength)
            f.write(str(datetime.now())+','+str(temp)+','+str(current)+','+str(ser)+'\n')
            print (" cycles = 0x%-12X"%(cycles))
            print (" errors = 0x%-12X"%(errors))
            print (" ones   = 0x%-12X target=0x%-12X"%(ones,cycles/M))
            print (" SlotER = %e"%(ser))
            print ('Begin Algorithm')
            start_time = datetime.now()           
            curr_time = datetime.now()
            ntemp = temp
            ncurrent = current
            while (True):

                cycles,errors,ones,ser = fpga.measureSER(obslength=obslength)
                #initialize average ser list; average value of last 3 values
                avg_ser = []
                stable = False
                avg_ser.insert(0,ser)
                if len(avg_ser) == 4:
                    if abs(ser-sum(avg_ser[1:])/3)<=ser and ser<=1e-4:
                        stable = True
                    avg_ser.pop()

                tser = ser #keep track of last temperature_ser to differentiate from current_ser
                curr_time = datetime.now()
                #Vary temperature by smallest resolution zzz
                zzz = 0.1
                ntemp = ntemp + zzz
                controller.setLaserTemp(ntemp)
                time.sleep(2)
                ncycles, nerrors, nones, nser = fpga.measureSER(obslength=obslength)
                f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                print ("New temperature: %f, nser: %e" %(ntemp, nser))
                while (nser < tser)  and nser != 0:
                    #safety check
                    if (ntemp >= 50):
                        print ("temp exceeded")
                        break
                    tser = nser
                    ntemp = ntemp + zzz
                    controller.setLaserTemp(ntemp)
                    time.sleep(5)
                    ncycles, nerrors, nones, nser = fpga.measureSER(obslength=obslength)
                    print ("New temperature: %f, nser: %e" %(ntemp,nser))
                    f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                #increasing temperature results in worse ser
                #revert back to last temperature and go in reverse direction
                if (nser > (tser+1*10**(m.floor(m.log10(abs(tser)))))) and nser != 0 and (tser<1e-2):
                    tser = nser
                    ntemp = ntemp - zzz
                    controller.setLaserTemp(ntemp)
                    time.sleep(5)
                    ncycles, nerrors, nones, nser = fpga.measureSER(obslength=obslength)
                    f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                    print ("New temperature %f, nser: %e" %(ntemp, nser))
                    while (nser <= tser) and ser != 0:
                        tser = nser
                        ntemp = ntemp - zzz
                        controller.setLaserTemp(ntemp)
                        time.sleep(5)
                        ncycles, nerrors, nones, nser = fpga.measureSER(obslength=obslength)
                        f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                        print ("New temperature: %f, nser: %e" %(ntemp,nser))
                    #if (nser > tser):
                        #ntemp = ntemp + zzz
                tser = nser #update tser before adjusting current
                print ("Current temperature: %f, current ser: %e" %(ntemp,tser))
                f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(ser)+'\n')           
               
                #Vary Current by smallest resolution ccc (only start after SER is above noise floor)
                if (tser<1e-2):
                    cser = tser #keep track of current_ser to differentiate from temperature_ser
                    ccc = 0.1
                    ncurrent = ncurrent + ccc
                    controller.setLaserCurrent(ncurrent)
                    time.sleep(2)
                    ncycles, nerrors, nones, nser = fpga.measureSER(obslength=obslength)
                    print ("New current: %f, nser: %e" %(ncurrent, nser)) 
                    f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')

                    avg_ser = []
                    while (nser < cser) and nser != 0 :
                        #safety check
                        if (ncurrent >= 138):
                            print ("curr exceeded")
                            break
                        cser = nser
                        ncurrent = ncurrent + ccc
                        controller.setLaserCurrent(ncurrent)
                        time.sleep(2)
                        ncycles, nerrors, nones, nser = fpga.measureSER(obslength=obslength)
                        print ("New current: %f, nser: %e" %(ncurrent,nser))
                        f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                    #increasing current results in worst ser
                    if (nser > (cser))  and nser != 0:
                        cser = nser
                        ncurrent = ncurrent - ccc
                        controller.setLaserCurrent(ncurrent)
                        time.sleep(2)
                        ncycles,nerrors,nones,nser = fpga.measureSER(obslength=obslength)
                        f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                        print ("New current: %f, nser: %e" %(ncurrent,nser))
                        while (nser < cser) and nser!= 0:
                            cser = nser
                            ncurrent = ncurrent - ccc
                            controller.setLaserCurrent(ncurrent)
                            time.sleep(2)
                            ncycles, nerrors, nones, nser = fpga.measureSER(obslength=obslength)
                            f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                            print ("New current: %f, nser: %e" %(ncurrent,nser))
                        #if (nser > cser):
                            #ncurrent = ncurrent + ccc
                    print ("Current curr: %f" %(ncurrent))

                f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                #If SER reaches minimum, peak power achieved
                if (nser <= 1e-5):
                    print ("Minimum SER reached, algorithm ending; ntemp: %f; ncurrent: %f"%(ntemp,ncurrent))
                    #save temp,current setpoint values
                    f.write(str(ntemp)+','+str(ncurrent)+'\n')
                    break
                #power optimization
            f.close()
        elif (mode == 1):
            #dither mode
            current = controller.getLaserCurrent()
           
           #controller.setLaserCurrent(current)
            
            #time.sleep(2)
            #while not (current - 0.1 <= round(controller.getLaserCurrent(),1) <= current + 0.1):
                #controller.setLaserCurrent(current)
                #time.sleep(1)
            
            temp = controller.getLaserTemp()
            #controller.setLaserTemp(temp)
            #time.sleep(2)
            #while not(round(controller.getLaserTemp(),1) == round(temp,1)):
                #time.sleep(1)

            #get temp/current again since commanded current/temp may not be 100% accurate
            #temp = controller.getLaserTemp()
            #current = controller.getLaserCurrent()
            print ("Old temperature: %f, Old current: %f"%(temp, current))
            print ("Measuring slot error rate...")
            cycles,errors,ones,ser = fpga.measureSER(obslength=obslength)
            f.write(str(datetime.now())+','+str(temp)+','+str(current)+','+str(ser)+'\n')
            print (" cycles = 0x%-12X"%(cycles))
            print (" errors = 0x%-12X"%(errors))
            print (" ones   = 0x%-12X target=0x%-12X"%(ones,cycles/M))
            print (" SlotER = %e"%(ser))
            print ('Begin Algorithm')
            start_time = datetime.now()           
            curr_time = datetime.now()
            ntemp = temp
            ncurrent = current
            while (True):

                cycles,errors,ones,ser = fpga.measureSER(obslength=obslength)
                if True:
                    cser = ser 
                    ccc = 0.1
                    ncurrent = ncurrent + ccc
                    controller.setLaserCurrent(ncurrent)
                    time.sleep(2)
                    ncycles, nerrors, nones, nser = fpga.measureSER(obslength=obslength)
                    print ("New current: %f, nser: %e" %(ncurrent, nser)) 
                    f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')

                    avg_ser = []
                    
                    if (nser < cser) and nser != 0:
                        while (nser < cser) and nser != 0 :
                            #safety check
                            if (ncurrent >= 138):
                                print ("curr exceeded")
                                break
                            cser = nser
                            ncurrent = ncurrent + ccc
                            controller.setLaserCurrent(ncurrent)
                            time.sleep(2)
                            ncycles, nerrors, nones, nser = fpga.measureSER(obslength=obslength)
                            print ("New current: %f, nser: %e" %(ncurrent,nser))
                            f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                    elif (nser == cser):
                        ncurrent = ncurrent - ccc
                        controller.setLaserCurrent(ncurrent)
                        time.sleep(2)
                        ncycles,nerrors,nones,nser = fpga.measureSER(obslength=obslength)
                        f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                        print ("New current: %f, nser: %e" %(ncurrent, nser))
                    
                    #increasing current results in worst ser
                    elif (nser > (cser))  and nser != 0:
                        cser = nser
                        ncurrent = ncurrent - ccc
                        controller.setLaserCurrent(ncurrent)
                        time.sleep(2)
                        ncycles,nerrors,nones,nser = fpga.measureSER(obslength=obslength)
                        f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                        print ("New current: %f, nser: %e" %(ncurrent,nser))
                        while (nser < cser) and nser!= 0:
                            cser = nser
                            ncurrent = ncurrent - ccc
                            controller.setLaserCurrent(ncurrent)
                            time.sleep(2)
                            ncycles, nerrors, nones, nser = fpga.measureSER(obslength=obslength)
                            f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                            print ("New current: %f, nser: %e" %(ncurrent,nser))
                        #if (nser > cser):
                            #ncurrent = ncurrent + ccc
                    print ("Current curr: %f" %(ncurrent))
                f.write(str(datetime.now())+','+str(ntemp)+','+str(ncurrent)+','+str(nser)+'\n')
                #If SER reaches minimum, peak power achieved
                if (nser <= ser):
                    print ("Minimum SER reached, algorithm ending; ntemp: %f; ncurrent: %f"%(ntemp,ncurrent))
                    #save temp,current setpoint values
                    f.write(str(ntemp)+','+str(ncurrent)+'\n')
                    #break
                #power optimization
            f.close()

def data_to_write(argList, fpga, writechannel, resetchannel, statuschannel, writedelay, vp, N, num_bytes):
    """
    Writes binary data to FPGA board.

    Args:
        argList(namespace): populated namespaced object with necessary args
        fpga(NodeFPGA): object representing FPGA board
        writechannel(int): conduit to use for writing to board
        resetchannel(int): conduit to use for reset to board
        statuschannel(int): channel to use for reading status from board
        writedelay(float): delay for writing used when writing files to board
        vp(): vendor and product ID 
        M(int): ppm order
    """
    if argList.f:
        dataFile = argList.f[0]
        try:
            data_packets = fpga.loadDataFile(dataFile,num_bytes)
        except:
            raise NameError('Must input a PPM order or wrong name of file')
        if argList.N:
            N = int(argList.N[0])
            fpga.writeFileNTimes(writechannel,resetchannel,statuschannel,data_packets,writedelay,vp,N)
            fpga.setTrackingMode(writechannel,trackingbyte,M) # quick hack, but should be doing tracking mode after a frame already
        else:
            fpga.writeFile(writechannel,resetchannel,statuschannel,data_packets,writedelay,vp)
            fpga.setTrackingMode(writechannel,trackingbyte,M) # quick hack, but should be doing tracking mode after a frame already

if __name__ == '__main__':
    main()