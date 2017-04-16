
from datetime import datetime

import gps
import time

import RPi.GPIO as GPIO
import smbus

import struct
import geopy.distance


print "GPS Starting"
# Open a file
fo = open("gpslog.txt", "wb")


################

# WXLink Test Setup
WXLinkResetPin = 12

WXLink_LastMessageID = 0
WXLink_LastMessageID_2 = 0
WXLink_LastMessageID_3 = 0

GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.OUT)
GPIO.output(4, 0)

GPIO.output(4,1)
time.sleep(0.25)
GPIO.output(4, 0)
time.sleep(0.25)
GPIO.output(4,1)
time.sleep(0.25)
GPIO.output(4, 0)
time.sleep(0.25)


WXLink_Data_Fresh = False

WXLink = smbus.SMBus(1)
try:
        data1 = WXLink.read_i2c_block_data(0x08, 0)
        WXLink_Present = True

        # OK, now export i2c to so we can determine if we need to reset WXLink
        os.system("echo '3' > /sys/class/gpio/export")
except:
        WXLink_Present = False

block1 = ""
block2 = ""



import crcpython2

# read WXLink and return list to set variables
crcCalc = crcpython2.CRCCCITT(version='XModem')



def readWXLink(block1, block2):
		global WXLink_LastMessageID
		global WXLink_LastMessageID_2
		global WXLink_LastMessageID_3
                global WXLink_Data_Fresh

                oldblock1 = block1
                oldblock2 = block2

                try:
                        block1 = WXLink.read_i2c_block_data(0x08, 0);
                        block2 = WXLink.read_i2c_block_data(0x08, 1);
                        block1_orig = block1
                        block2_orig = block2
                        stringblock1 = ''.join(chr(e) for e in block1)
                        stringblock2 = ''.join(chr(e) for e in block2[0:27])

                        block1 = bytearray(block1)
                        block2 = bytearray(block2)
                except:
                        block1 = oldblock1
                        block2 = oldblock2
                        block1_orig = block1
                        block2_orig = block2
                        print "b1, b2=", block1, block2
                        stringblock1 = ''.join(chr(e) for e in block1)
                        stringblock2 = ''.join(chr(e) for e in block2[0:27])

                        block1 = bytearray(block1)
                        block2 = bytearray(block2)

                if ((len(block1) > 0) and (len(block2) > 0)):
                        # check crc for errors - don't update data if crc is bad

                        #get crc from data
                        receivedCRC = struct.unpack('H', str(block2[29:31]))[0]
                        #swap bytes for recievedCRC
                        receivedCRC = (((receivedCRC)>>8) | ((receivedCRC&0xFF)<<8))&0xFFFF
                        calculatedCRC = crcCalc.calculate(block1+block2[0:27])


                        # check for start bytes, if not present, then invalidate CRC

                        if (block1[0] != 0xAB) or (block1[1] != 0x66):
                                calculatedCRC = receivedCRC + 1

                        if (receivedCRC == calculatedCRC):

                                # message ID
                                SensorID = block1[2]/10
                                MessageID = struct.unpack('l', str(block2[25:29]))[0]

                                currentWindGust = 0.0   # not implemented in Solar WXLink version

                                totalRain = struct.unpack('l', str(block1[17:21]))[0]


                                currentWindSpeed = struct.unpack('f', str(block1[9:13]))[0]

                                currentWindDirection = struct.unpack('H', str(block1[7:9]))[0]

                                # now do the AM2315 Temperature
                                temperature = struct.unpack('f', str(block1[25:29]))[0]
                                elements = [block1[29], block1[30], block1[31], block2[0]]
                                outHByte = bytearray(elements)
                                humidity = struct.unpack('f', str(outHByte))[0]



                                # now read the SunAirPlus Data from WXLink

                                batteryVoltage = struct.unpack('f', str(block2[1:5]))[0]
                                batteryCurrent = struct.unpack('f', str(block2[5:9]))[0]
                                loadCurrent = struct.unpack('f', str(block2[9:13]))[0]
                                solarPanelVoltage = struct.unpack('f', str(block2[13:17]))[0]
                                solarPanelCurrent = struct.unpack('f', str(block2[17:21]))[0]

                                auxA = struct.unpack('f', str(block2[21:25]))[0]



                                if (SensorID == 3):
                                        if (WXLink_LastMessageID_3 != MessageID):
                                                WXLink_Data_Fresh = True
                                                WXLink_LastMessageID_3 = MessageID
                                                print "WXLink_Data_Fresh set to True"

                                                print "********************"
                                                now = datetime.now().strftime('%H:%M:%S - %Y/%m/%d')
                                                print "Wireless ID/Mess#=%d/%i\t %s SVer = %d BV=%6.2f SV=%6.2f SC=%6.2f" % (SensorID, MessageID, now, (block1[2] - block1[2]/10*10), batteryVoltage, solarPanelVoltage, solarPanelCurrent)
                                                print "********************"




                        else:
                                print "Bad CRC Received"
                                return []

                else:
                        return []

                # return list
                returnList = []
                returnList.append(block1_orig)
                returnList.append(block2_orig)
                returnList.append(currentWindSpeed)
                returnList.append(currentWindGust)
                returnList.append(totalRain)
                returnList.append(currentWindDirection)
                returnList.append(temperature)
                returnList.append(humidity)
                returnList.append(batteryVoltage)
                returnList.append(batteryCurrent)
                returnList.append(loadCurrent)
                returnList.append(solarPanelVoltage)
                returnList.append(solarPanelCurrent)
                returnList.append(auxA)
                returnList.append(MessageID)
		returnList.append(SensorID)

                return returnList


# Listen on port 2947 (gpsd) of localhost
session = gps.gps("localhost", "2947")
session.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)

# home location
coords_1 = (47.676841667, -117.135241667)

everyHowManySeconds = 2
print "GPS Loop"
while True:
        try:

                report = session.next()
                # Wait for a 'TPV' report and display the current time
                # To see all report data, uncomment the line below
                #print report
		seconds=int(time.time())
		
                if report['class'] == 'TPV':
			if (seconds % everyHowManySeconds ) == 0:
				returnList = readWXLink(block1, block2)

                		#print report
                        	if hasattr(report, 'time'):
                                	print report.time


                        	if hasattr(report, 'lat'):
					#GPS location
					coords_2 = (report.lat, report.lon)
					distance = geopy.distance.vincenty(coords_1, coords_2).km
					print "distance in km = %0.3f"% distance

				if (WXLink_Data_Fresh):
					LoRaReceived=1
					WXLink_Data_Fresh = False
					LoRaMessID = returnList[14]
					// do a double beep
					GPIO.output(4,1)
					time.sleep(0.10)
					GPIO.output(4, 0)
					time.sleep(0.10)
					GPIO.output(4,1)
					time.sleep(0.10)
					GPIO.output(4, 0)
					time.sleep(0.10)


				else:
					LoRaReceived = 0
					LoRaMessID = 0


                        	if hasattr(report, 'time'):
					logValue = "no Data"
                        		if hasattr(report, 'lat'):
						logValue = "%s, %f, %f, %0.2f, %0.2f, %i, %i %0.3f\n" % (report.time, report.lat, report.lon,report.alt, report.speed,LoRaReceived, LoRaMessID, distance)
                               		fo.write(logValue);
					fo.flush()

        except KeyError:
                pass
        except KeyboardInterrupt:
                quit()
        except StopIteration:
                session = None
                print "GPSD has terminated"
fo.close()
# Close opened file
