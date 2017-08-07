#include <unistd.h>
#include <atomic>
#include <csignal>
#include <chrono>
#include <thread>
#include "pigpiod_if2.h"

#include "log.h"
#include "fsm.h"
#include "camera.h"
#include "processing.h"
#include "tracking.h"
#include "calibration.h"
#include "link.h"

//#define CAL_LASER_PIN 4

atomic<bool> stop(false);

//-----------------------------------------------------------------------------
int mainLoop()
//-----------------------------------------------------------------------------
{
	// Synchronization
	enum Phase { START, CALIBRATION, ACQUISITION, OPEN_LOOP, CL_INIT, CL_BEACON, CL_CALIB };

	// Connection to GUI
	Link link("http://10.0.5.1:3000");

	// GPIO init
	int gpioHandle = pigpio_start(0, 0);
	if(gpioHandle < 0)
	{
		log(std::cerr, "Failed to initialize GPIO!");
		exit(1);
	}

	// Hardware init
	Camera camera;
	FSM fsm(gpioHandle, SPI0_CE0, PWM0, GPIO6, 80, 129, 200);
	Calibration calibration(camera, fsm);
	Tracking track(camera, calibration);

	// Cal laser switching
	set_mode(gpioHandle, 4, PI_OUTPUT);

	// Killing app handler
	signal(SIGINT, [](int signum) { stop = true; });

	// Tracking variables
	Phase phase = START;
	Group beacon, calib;
	AOI beaconWindow, calibWindow;
	int currentExposure = 0, spotIndex = 0;
	int beaconGain = 0, calibGain = 0;
	bool haveBeaconKnowledge = false, haveCalibKnowledge = false;
	double propertyDifference = 0;

	// Offset changes from GUI
	atomic<int> centerOffsetX(5), centerOffsetY(32);
	link.on("offsets", [&](sio::event& ev)
	{
		centerOffsetX = ev.get_message()->get_map()["x"]->get_int();
		centerOffsetY = ev.get_message()->get_map()["y"]->get_int();
		log(std::cout, "Center offset updated to [", centerOffsetX, ",", centerOffsetY, "]");
	});

	// Main loop
	for(int i = 1; ; i++)
	{
		switch(phase)
		{
			case START:
				gpio_write(gpioHandle, 4, 0);
				logAndConfirm("Start calibration with Enter...");
				gpio_write(gpioHandle, 4, 1);
				phase = CALIBRATION;
				break;

			// Calibration phase, internal laser has to be turned on, ran just once
			case CALIBRATION:
				fsm.enableAmp();
				if(calibration.run(calib))
				{
					gpio_write(gpioHandle, 4, 0);
					logAndConfirm("Done! Start beacon acquisition with Enter...");
					phase = ACQUISITION;
				}
				else
				{
					log(std::cerr, "Calibration failed!");
					phase = START;
				}
				break;

			// Beacon acquisition phase, internal laser has to be off!
			case ACQUISITION:
				if(track.runAcquisition(beacon))
				{
					// Acquisition passed!
					haveBeaconKnowledge = true;
					haveCalibKnowledge = false;
					// Save all important parameters
					currentExposure = camera.config->expose_us.read();
					beaconGain = camera.config->gain_dB.read();
					calibGain = calibration.gainForExposure(currentExposure);
					log(std::cout, "Acquistion complete:", currentExposure, "us ; beacon:",
						beaconGain, "dB smoothing", track.beaconSmoothing, "; calib:",
						calibGain, "dB smoothing", calibration.smoothing);
					// Set initial pointing in open-loop
					calib.x = 2*((CAMERA_WIDTH/2) + centerOffsetX) - beacon.x;
					calib.y = 2*((CAMERA_HEIGHT/2) + centerOffsetY) - beacon.y;
					track.controlOpenLoop(fsm, calib.x, calib.y);
					// logAndConfirm("Start open-loop tracking with Enter...");
					// camera.fillRequestQueue();
					phase = CL_INIT;
				}
				break;

			// Control in open-loop, sampling only beacon spot!
			case OPEN_LOOP:
				if(camera.waitForFrame())
				{
					Image frame(camera, track.beaconSmoothing);
					if(frame.histBrightest > TRACK_ACQUISITION_BRIGHTNESS &&
					   frame.performPixelGrouping() > 0 && (
					   spotIndex = track.findSpotCandidate(frame, beacon, &propertyDifference)) >= 0 &&
					   frame.groups[spotIndex].valueMax > TRACK_ACQUISITION_BRIGHTNESS)
					{
						Group& spot = frame.groups[spotIndex];
						// Check spot properties
						if(propertyDifference < TRACK_MAX_SPOT_DIFFERENCE)
						{
							haveBeaconKnowledge = true;
							// Update values if confident
							beacon.x = frame.area.x + spot.x;
							beacon.y = frame.area.y + spot.y;
							beacon.valueMax = spot.valueMax;
							beacon.valueSum = spot.valueSum;
							beacon.pixelCount = spot.pixelCount;
							track.updateTrackingWindow(frame, spot, beaconWindow);
							// Control pointing in open-loop
							calib.x = 2*((CAMERA_WIDTH/2) + centerOffsetX) - beacon.x;
							calib.y = 2*((CAMERA_HEIGHT/2) + centerOffsetY) - beacon.y;
							track.controlOpenLoop(fsm, calib.x, calib.y);
						}
						else
						{
							if(haveBeaconKnowledge) log(std::cout, "Panic, rapid beacon spot property change, old", beacon.x, beacon.y, beacon.pixelCount,
								beacon.valueMax, "new", frame.area.x + spot.x, frame.area.y + spot.y, spot.pixelCount, spot.valueMax);
							haveBeaconKnowledge = false;
						}
					}
					else
					{
						if(haveBeaconKnowledge) log(std::cout, "Panic, beacon spot vanished!");
						haveBeaconKnowledge = false;
					}
					// Send image to GUI
					link.setBeacon(frame);
					// Request new frame
					camera.setWindow(beaconWindow);
					camera.requestFrame();
				}
				break;

			// Initialize closed-loop double window tracking
			case CL_INIT:
				camera.ignoreNextFrames(camera.queuedCount);
				// Init flipping windows - first window
				camera.config->gain_dB.write(beaconGain);
				camera.setWindow(beaconWindow);
				camera.requestFrame();
				// Request second window
				camera.config->gain_dB.write(calibGain);
				calibWindow.x = calib.x - TRACK_ACQUISITION_WINDOW/2;
				calibWindow.y = calib.y - TRACK_ACQUISITION_WINDOW/2;
				calibWindow.w = TRACK_ACQUISITION_WINDOW;
				calibWindow.h = TRACK_ACQUISITION_WINDOW;
				// Initial values will be uncertain
				calib.pixelCount = 0;
				camera.setWindow(calibWindow);
				camera.requestFrame();
				log(std::cout, "Double window tracking set up! Queued", camera.queuedCount, "requests");
				// Next up is beacon spot frame
				phase = CL_BEACON;
				break;

			// Process new frame of beacon spot
			case CL_BEACON:
				if(camera.waitForFrame())
				{
					Image frame(camera, track.beaconSmoothing);
					if(frame.histBrightest > TRACK_ACQUISITION_BRIGHTNESS &&
					   frame.performPixelGrouping() > 0 && (
					   spotIndex = track.findSpotCandidate(frame, beacon, &propertyDifference)) >= 0 &&
					   frame.groups[spotIndex].valueMax > TRACK_ACQUISITION_BRIGHTNESS)
					{
						Group& spot = frame.groups[spotIndex];
						// Check spot properties
						if(propertyDifference < TRACK_MAX_SPOT_DIFFERENCE)
						{
							haveBeaconKnowledge = true;
							// Update values if confident
							beacon.x = frame.area.x + spot.x;
							beacon.y = frame.area.y + spot.y;
							beacon.valueMax = spot.valueMax;
							beacon.valueSum = spot.valueSum;
							beacon.pixelCount = spot.pixelCount;
							track.updateTrackingWindow(frame, spot, beaconWindow);
						}
						else
						{
							if(haveBeaconKnowledge) log(std::cout, "Panic, rapid beacon spot property change, old", beacon.x, beacon.y, beacon.pixelCount,
								beacon.valueMax, "new", frame.area.x + spot.x, frame.area.y + spot.y, spot.pixelCount, spot.valueMax);
							haveBeaconKnowledge = false;
						}
					}
					else
					{
						if(haveBeaconKnowledge) log(std::cout, "Panic, beacon spot vanished!");
						haveBeaconKnowledge = false;
					}
					// Send image to GUI
					link.setBeacon(frame);
					// Request new frame
					camera.setWindow(beaconWindow);
					camera.config->gain_dB.write(beaconGain);
					camera.requestFrame();
					// Next up is calibration laser frame
					phase = CL_CALIB;
				}
				else
				{
					log(std::cerr, "Out of sync, re-initializing!", camera.error);
					phase = CL_INIT;
				}
				break;

			// Process new frame of calib laser spot
			case CL_CALIB:
				if(camera.waitForFrame())
				{
					Image frame(camera, calibration.smoothing);
					if(frame.histBrightest > CALIB_MIN_BRIGHTNESS/4 &&
					   frame.performPixelGrouping() > 0 && (
					   spotIndex = track.findSpotCandidate(frame, calib, &propertyDifference)) >= 0 &&
					   frame.groups[spotIndex].valueMax > CALIB_MIN_BRIGHTNESS/4)
					{
						Group& spot = frame.groups[spotIndex];
						// Check spot properties
						if(propertyDifference < TRACK_MAX_SPOT_DIFFERENCE)
						{
							haveCalibKnowledge = true;
							// Update values if confident
							calib.x = frame.area.x + spot.x;
							calib.y = frame.area.y + spot.y;
							// calib.valueMax = spot.valueMax;
							// calib.valueSum = spot.valueSum;
							// calib.pixelCount = spot.pixelCount;
							track.updateTrackingWindow(frame, spot, calibWindow);
							// Control in closed loop!
							track.control(fsm, calib.x, calib.y, 2*((CAMERA_WIDTH/2) + centerOffsetX) - beacon.x, 2*((CAMERA_HEIGHT/2) + centerOffsetY) - beacon.y);
						}
						else
						{
							if(haveCalibKnowledge) log(std::cout, "Panic, rapid calib spot property change, old", calib.x, calib.y, calib.pixelCount,
								calib.valueMax, "new", frame.area.x + spot.x, frame.area.y + spot.y, spot.pixelCount, spot.valueMax);
							haveCalibKnowledge = false;
						}
					}
					else
					{
						if(haveCalibKnowledge)
						{
							log(std::cout, "Panic, calib spot vanished!");
							// Try forced FSM SPI transfer? Maybe data corruption
							fsm.forceTransfer();
						}
						haveCalibKnowledge = false;
					}
					// Send image to GUI
					link.setCalib(frame);
					// Request new frame
					camera.setWindow(calibWindow);
					camera.config->gain_dB.write(calibGain);
					camera.requestFrame();
					// Next up is beacon laser frame
					phase = CL_BEACON;
				}
				else
				{
					log(std::cerr, "Out of sync, re-initializing!", camera.error);
					phase = CL_INIT;
				}
				break;

			// Fail-safe
			default:
				log(std::cerr, "Something went terribly wrong!");
				phase = START;
				break;
		}

		// Debug periodic console update
		if(i % 200 == 0)
		{
			if(phase == OPEN_LOOP)
			{
				log(std::cout, haveBeaconKnowledge ? "Beacon is at" : "No idea where beacon is",
					"[", beacon.x, ",", beacon.y, "]");
			}
			else
			{
				log(std::cout, haveBeaconKnowledge ? "Beacon is at" : "No idea where beacon is",
					"[", beacon.x, ",", beacon.y, "]", haveCalibKnowledge ? "Calib is at" : "No idea where calib is",
					"[", calib.x, ",", calib.y, "]");
			}
			i = 0;
		}

		// GUI update (manages FPS itself)
		link.sendUpdate(haveBeaconKnowledge, haveCalibKnowledge, beacon.x, beacon.y, calib.x, calib.y, track.actionX, track.actionY);

		// Allow exit with Ctrl-C
		if(stop) break;
	}

	log(std::cout, "\nFinishing...");
	fsm.disableAmp();

	return 0;
}

BOOST_PYTHON_MODULE(camFSMcontrol) {
	using namespace boost::python;

	def("mainLoop", mainLoop);
}
