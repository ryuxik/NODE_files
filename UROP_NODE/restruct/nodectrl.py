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
# NODE FPGA Commander Copyright (C) 2015 Ryan Kingsbury
# -Updated and restructured by Santiago Munoz 2017

import fl
import argparse
import time
import struct
import csv
from datetime import datetime
from node import NodeFPGA
import sys

DEBUG = False

# FPGA image, update with new image directory
FPGA_IMAGE = "/home/kingryan/Dropbox/grad_school/fpga/makestuff/hdlmake/apps/roamingryan/swled/bist/vhdl/top_level.xsvf"

# File-reader which yields chunks of data
def readFile(fileName):
    with open(fileName, "rb") as f:
        while True:
            chunk = f.read(32768)
            if chunk:
                yield chunk
            else:
                break

# gets args from command line input
def get_args():    
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

# handles ids when flOpen fails
def ids(vp, argList):
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

# selects conduit and checks if the FPGA board is nero capable and capable of communication 
def conduit_selection(argList_c=1):
    isNeroCapable = fl.flIsNeroCapable(handle)
    isCommCapable = fl.flIsCommCapable(handle, conduit)
    fl.flSelectConduit(handle, conduit)
    return (isNeroCapable, isCommCapable)

# tests the JTAG chain
def jtag_chain(isNeroCapable, argList, vp, handle):
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

# configures FPGA board with selected program
def configure(argList, isNeroCapable, handle, vp):
    if argList.p:
        progConfig = argList.p[0]
        print("Programming device with config {}...".format(progConfig))
        if isNeroCapable:
            fl.flProgram(handle, progConfig)
        else:
            raise fl.FLException("Device program requested but device at {} does not support NeroProg".format(vp))

#writes bin data to fpga
def data_to_write(argList, fpga, writechannel, resetchannel, statuschannel, writedelay, vp, N, num_bytes):
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
                
def main():
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
        
        # if ( argList.d ):
        #     print("Configuring ports...")
        #     rb = "{:0{}b}".format(fl.flMultiBitPortAccess(handle, argList.d[0]), 32)
        #     print("Readback:   28   24   20   16    12    8    4    0\n          {} {} {} {}  {} {} {} {}".format(
        #         rb[0:4], rb[4:8], rb[8:12], rb[12:16], rb[16:20], rb[20:24], rb[24:28], rb[28:32]))
        #     fl.flSleep(100)

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
               # dacval = int(eval(argList.dac[0]))
               # print ("Setting DAC value to %i (0x%X)"%(dacval,dacval))
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
        
    except fl.FLException as ex:
        print(ex)
    finally:
        fl.flClose(handle)

if __name__ == '__main__':
    main()