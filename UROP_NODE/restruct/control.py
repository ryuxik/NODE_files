#!/usr/bin/env python
#
# Copyright (C) 2009-2014 Chris McClelland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
This is the consolidated control file, includes funcitons from 
nodectrl, nodectrl_oven_test, and SPI_test

NODE FPGA Commander Copyright (C) 2015 Ryan Kingsbury
-Updated and restructured by Santiago Munoz and Ethan Munden 2017
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
from optimizer import Optimizer
from mmap import tester

#Also not sure where this DEBUG is used
#DEBUG = False

# FPGA image, must update with new directory/ host on rpi cm3!!!
# Actually, not sure what where this is used 
#FPGA_IMAGE = "/home/kingryan/Dropbox/grad_school/fpga/makestuff/hdlmake/apps/roamingryan/swled/bist/vhdl/top_level.xsvf"

def readFile(fileName):
    """
    File-reader which yields chunks of data

    Args:
        fileName(string): name of file to read
    Yields:
        chunk(string): data read from file opened
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


def data_to_write(argList, fpga, writechannel, resetchannel, statuschannel, writedelay, vp, M, num_bytes):
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

def update_SPI(handle, channels, byte_array):
    """
    Updates SPI

    Args:
        handle: An opaque reference to an internal structure representing the connection.
        channels(list): channles to be used as conduits
        byte_array(list): list of bytes
    """
    MSB_channel = channels[0]
    LSB_channel = channels[1]
    fl.flWriteChannel(handle, MSB_channel, byte_array[0])
    fl.flWriteChannel(handle, LSB_channel, byte_array[1])

def read_SPI(handle, channels):
    """
    Reads the SPI

    Args:
        handle: An opaque reference to an internal structure representing the connection.
        channels(list): channles to be used as conduits

    Returns:
        (list): rxm and rxl read from channels specified
    """
    MSB_channel = channels[0]
    LSB_channel = channels[1]
    rxm = fl.flReadChannel(handle, MSB_channel)
    rxl = fl.flReadChannel(handle, LSB_channel)
    return [rxm, rxl]

#main function of the old SPI_test
#need to fix so this uses Optimizer object
def SPImain():
	argList = get_args()
	handle = fl.FLHandle()
	try:
	    fl.flInitialise(0)
	    vp = argList.v[0]
	    print("Attempting to open connection to FPGALink device {}...".format(vp))
	    try:
	        handle = fl.flOpen(vp)
	    except fl.FLException as ex:
	        if argList.i:
	            ivp = argList.i[0]
	            print("Loading firmware into {}...".format(ivp))
	            fl.flLoadStandardFirmware(ivp, vp)
                mem_map = tester(ivp, vp)

	            # Long delay for renumeration
	            # TODO: fix this hack.  The timeout value specified in flAwaitDevice() below doesn't seem to work
	            time.sleep(3)
	            
	            print("Awaiting renumeration...")
	            if not fl.flAwaitDevice(vp, 10000):
	                raise fl.FLException("FPGALink device did not renumerate properly as {}".format(vp))

	            print("Attempting to open connection to FPGALink device {} again...".format(vp))
	            handle = fl.flOpen(vp)
	        else:
	            raise fl.FLException("Could not open FPGALink device at {} and no initial VID:PID was supplied".format(vp))
	    
	    # if ( argList.d ):
	    #     print("Configuring ports...")
	    #     rb = "{:0{}b}".format(fl.flMultiBitPortAccess(handle, argList.d[0]), 32)
	    #     print("Readback:   28   24   20   16    12    8    4    0\n          {} {} {} {}  {} {} {} {}".format(
	    #         rb[0:4], rb[4:8], rb[8:12], rb[12:16], rb[16:20], rb[20:24], rb[24:28], rb[28:32]))
	    #     fl.flSleep(100)

	    conduit = 1
	    if argList.c:
	        conduit = int(argList.c[0])

	    isNeroCapable = fl.flIsNeroCapable(handle)
	    isCommCapable = fl.flIsCommCapable(handle, conduit)
	    fl.flSelectConduit(handle, conduit)
	   
	    if argList.f and not(isCommCapable):
	        raise fl.FLException("Data file load requested but device at {} does not support CommFPGA".format(vp))

	    if isCommCapable and fl.flIsFPGARunning(handle):
	        fpga = NodeFPGA(handle)
            opt = Optimizer(handle, fpga)
	        #Test setting LD Bias to 0.150A (channels 26, 27)

            #opt.setCurrent(0.150)
            #this section of code looks like setLaserCurrent()

	        curr = 0.150
	        code = curr/(4.096*1.1*((1/6.81)+(1/16500)))*4096
	        first_byte, second_byte = opt.code2bytes(code)
	        spi_data = [first_byte, second_byte]
	        update_SPI(handle, [26,27], spi_data)
	        #Test reading LD Bias (channels 64 and 65)
	        rx_bias = read_SPI(handle, [mem_map.getAddress('CC3a'), mem_map.getAddress('CC3b')])
	        for r in rx_bias:
	            print "Bias bytes read: ", r
	        print (rx_bias[1]*256 + rx_bias[0])/4096 * (4.096*1.1*((1/6.81)+(1/16500)))

	        #Test writing/reading to LD Temp
	        #TODO Constants are estimated; may need to verify with vendor
	        R_known = 10000
	        Vcc = 0.8
	        B = 3900
	        R_0 = 10000
	        T_0 = 25 
	        #writing temp 35C
	        T = 35
	        V_set = Vcc/(((m.exp(B/T)*(R_0 * m.exp(-B/T_0)))/R_known)+1)
	        V_code = opt.voltage2code(V_set) #convert voltage to code
	        fb, sb = opt.code2byte(V_code) #convert code to bytes
	        update_SPI(handle, [mem_map.getAddress('LTSa'),mem_map.getAddress('LTSb')], [fb, sb])

	        #reading temp
	        bytes__meas = read_SPI(handle, [mem_map.getAddress('LTMa'),mem_map.getAddress('LTMb')]) #read ADC value
	        code_meas = bytes_meas[1]*256 + bytes_meas[0] #convert bytes to double
			V_meas = opt.code2voltage(code_meas) #convert ADC to voltage

	        R_t = R_known * (Vcc/V_meas - 1)
	        T = B/m.log(R_t/R_0 * m.exp(-B/T_0))
	        print ("Temp read: ", T)

	        #Test reading from RTD
	        A = 3.81e-3 #from datasheet
	        B = -6.02e-7 #from datasheet
	        R_t0 = 1000
	        T_bm = read_SPI(handle, [mem_map.getAddress('TE1a'),mem_map.getAddress('TE1b')]) #temp code measured
			T_cm = 256*T_bm[1] + T_bm[0] #convert bytes to double
	        T_meas = opt.code2voltage(T_cm) #convert ADC to voltage
	        R_T = R_known * (Vcc/T_meas - 1)
	        C = 1 -( R_T/R_t0)
	        T_R = (-A + (A**2-(4*B*C))**0.5) / (2*B)
	        print ("RTD temp: ", T_R)

	except fl.FLException as ex:
	    print(ex)
	finally:
	    fl.flClose(handle)

#main fucnition of the old nodectr_oven_test
def NODECTRLmain():
    argList = get_args()
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
            ##must update these channels 
            writechannel = 0x02
            statuschannel = 0x05
            resetchannel = 0x08

            writedelay,num_bytes,trackingbyte = fpga.setModulatorParams(M)

            if argList.ppm:
                M = int(eval(argList.ppm[0]))
                print ("Setting PPM order to: ",M)
                fpga.setPPM_M(M)

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

            data_to_write(argList, fpga, writechannel, resetchannel, statuschannel, writedelay, vp, M, num_bytes)
            #alg testing goes here, but alg is not up to date!!
            #opt_alg(argList, fpga)
            
    except fl.FLException as ex:
        print(ex)
    finally:
        fl.flClose(handle)