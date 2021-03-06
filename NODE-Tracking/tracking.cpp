// NODE Tracking algorithms
// Author: Ondrej Cierny
#include "tracking.h"
#include "log.h"
#include <cmath>

// Sweep through expected power ranges and look for spot
//-----------------------------------------------------------------------------
bool Tracking::runAcquisition(Group& beacon)
//-----------------------------------------------------------------------------
{
	uint16_t exposure = TRACK_MIN_EXPOSURE, gain = 0, skip = camera.queuedCount;

	camera.setFullWindow();
	camera.config->binningMode.write(cbmBinningHV);
	camera.config->expose_us.write(exposure);
	camera.config->gain_dB.write(gain);
	camera.requestFrame();

	// Skip pre-queued old frames
	camera.ignoreNextFrames(skip);

	// Sweep exposure times; running at ~16 fps at this point
	// This has to have top limit on calib laser saturation?!
	// We want to do gain flipping eventually
	for(exposure += 1000; exposure <= 10000; exposure += 1000)
	{
		if(camera.waitForFrame())
		{
			Image frame(camera);
			if(verifyFrame(frame) && windowAndTune(frame, beacon)) return true;
			camera.config->expose_us.write(exposure);
			camera.requestFrame();
		}
	}

	// Sweep gains
	// for(gain++; gain <= 10; gain++)
	// {
	// 	camera.config->gain_dB.write(gain);
	// 	for(int i = 0; i < camera.requestQueueSize; i++)
	// 	{
	// 		if(camera.waitForFrame())
	// 		{
	// 			Image frame(camera);
	// 			camera.requestFrame();
	// 			if(verifyFrame(frame) && windowAndTune()) return true;
	// 		}
	// 	}
	// }

	return false;
}

// TODO: This should have more sophisticated checks eventually
//-----------------------------------------------------------------------------
bool Tracking::verifyFrame(Image& frame)
//-----------------------------------------------------------------------------
{
	if(frame.histBrightest > TRACK_ACQUISITION_BRIGHTNESS &&
	   frame.histBrightest > frame.histPeak &&
	   frame.histBrightest - frame.histPeak > TRACK_GOOD_PEAKTOMAX_DISTANCE)
	{
		// All checks passed and we have some good groups!
		if(frame.performPixelGrouping() > 0)
		{
			log(std::cout, "Frame verified, tuning camera parameters");
			return true;
		}
		else log(std::cerr, "Frame has good properties but grouping did not succeed");
	}	
	return false;
}

// Make window around brightest area, fine tune exposure/gain with no binning
//-----------------------------------------------------------------------------
bool Tracking::windowAndTune(Image& frame, Group& beacon)
//-----------------------------------------------------------------------------
{
	// Prepare a small window around brightest group for tuning
	double fullX = frame.groups[0].x * 2, fullY = frame.groups[0].y * 2;
	int maxValue = frame.groups[0].valueMax;

	for(int8_t i = 0; i < TRACK_TUNING_MAX_ATTEMPTS; i++)
	{
		camera.config->binningMode.write(cbmOff);
		camera.setCenteredWindow(fullX, fullY, TRACK_ACQUISITION_WINDOW);
		camera.requestFrame();

		// Try tuning the windowed frame
		// log(std::cout, "Prepared windowed tuning frame at [", fullX, fullY, "]");
		bool success = autoTuneExposure(beacon);
		
		// Switch back to full frame
		camera.config->binningMode.write(cbmBinningHV);
		camera.setFullWindow();
		camera.requestFrame();

		// If passed, verify if we are on the right spot in full frame
		if(success)
		{
			if(camera.waitForFrame())
			{
				Image test(camera);
				if(test.performPixelGrouping() > 0)
				{
					if(abs(test.groups[0].x * 2 - fullX) < TRACK_TUNING_POSITION_TOLERANCE &&
					   abs(test.groups[0].y * 2 - fullY) < TRACK_TUNING_POSITION_TOLERANCE &&
					   abs((int)test.groups[0].valueMax - maxValue) < TRACK_TUNING_BRIGHTNESS_TOLERANCE)
					{
						// Tuned spot is at a good location, success
						camera.setCenteredWindow(fullX, fullY, TRACK_ACQUISITION_WINDOW);
						camera.config->binningMode.write(cbmOff);
						return true;
					}

					// Tuned the wrong area, repeat
					fullX = test.groups[0].x * 2;
					fullY = test.groups[0].y * 2;
					maxValue = test.groups[0].valueMax;
				}
				else break;
			}
			else break;
		}
		else return false;
	}
	log(std::cerr, "Freaky error in camera tuning");
	return false;
}

// Try auto tuning the exposure for the current spot
//-----------------------------------------------------------------------------
bool Tracking::autoTuneExposure(Group& beacon)
//-----------------------------------------------------------------------------
{
	AOI tuningWindow;

	// Helper testing inline function
	auto test = [&](bool desaturating) -> bool
	{
		camera.requestFrame();
		if(camera.waitForFrame())
		{
			Image test(camera, beaconSmoothing);
			if(test.performPixelGrouping() > 0)
			{
				Group& spot = test.groups[0];
				// Copy properties
				beacon.x = test.area.x + spot.x;
				beacon.y = test.area.y + spot.y;
				beacon.valueMax = spot.valueMax;
				beacon.valueSum = spot.valueSum;
				beacon.pixelCount = spot.pixelCount;
				if(desaturating && spot.valueMax <= TRACK_HAPPY_BRIGHTNESS) return true;
				if(!desaturating && spot.valueMax >= TRACK_HAPPY_BRIGHTNESS) return true;
				updateTrackingWindow(test, spot, tuningWindow);
				camera.setWindow(tuningWindow);
			}
		}
		return false;
	};

	// Grab a frame to determine the next step
	if(camera.waitForFrame())
	{
		Image frame(camera);
		if(frame.performPixelGrouping() > 0)
		{
			// Determine smoothing
			beaconSmoothing = calibration.determineSmoothing(frame);
			frame.applyFastBlur(beaconSmoothing);

			if(frame.performPixelGrouping() > 0)
			{
				// Check if we are actually good?
				if(abs((int)frame.groups[0].valueMax - TRACK_HAPPY_BRIGHTNESS) < TRACK_TUNING_TOLERANCE) return true;

				// Nah, update window and start changing parameters
				updateTrackingWindow(frame, frame.groups[0], tuningWindow);
				camera.setWindow(tuningWindow);

				if(frame.groups[0].valueMax > TRACK_HAPPY_BRIGHTNESS)
				{
					// Start decreasing gain if it's non-zero
					for(int gain = camera.config->gain_dB.read(); gain > 0; gain--)
					{
						camera.config->gain_dB.write(gain - 1);
						if(test(true)) return true;
					}

					// Start decreasing exposure
					for(int exposure = camera.config->expose_us.read(); exposure >= TRACK_MIN_EXPOSURE && exposure/TRACK_TUNING_EXP_DIVIDER >= 1; exposure -= exposure/TRACK_TUNING_EXP_DIVIDER)
					{
						camera.config->expose_us.write(exposure - exposure/TRACK_TUNING_EXP_DIVIDER);
						if(test(true)) return true;
					}

					// Camera reached lower limit, too high power
					log(std::cerr, "Unable to desaturate camera");
					return true;
				}
				// Otherwise, have to increase exposure
				else
				{
					// Start increasing exposure; again here top limit should be calib laser saturation
					for(int exposure = camera.config->expose_us.read(); exposure <= 10000; exposure += exposure/TRACK_TUNING_EXP_DIVIDER)
					{
						camera.config->expose_us.write(exposure + exposure/TRACK_TUNING_EXP_DIVIDER);
						if(test(false)) return true;
					}

					// Start increasing gain
					for(int gain = camera.config->gain_dB.read(); gain <= 10; gain++)
					{
						camera.config->gain_dB.write(gain + 1);
						if(test(false)) return true;
					}

					// Very high parameters reached
					log(std::cerr, "Unable to reach desired brightness with maximum parameters");
					return true;
				}
			}
		}
	}
	log(std::cerr, "Freaky error in exposure auto tuning");
	return false;
}

// Update camera window based on spot's size and its location in window
//-----------------------------------------------------------------------------
void Tracking::updateTrackingWindow(Image& frame, Group& spot, AOI& window)
//-----------------------------------------------------------------------------
{
	float spotWidth = sqrt(1.5f * (float)spot.pixelCount);
	float distanceLimit = spotWidth > TRACK_MIN_SPOT_LIMIT ? spotWidth : TRACK_MIN_SPOT_LIMIT;

	// Check maximum allowed width discrepancy due to quantization & tolerance
	// Then check if location of centroid is in good bounds
	if(abs(window.w - (spotWidth + 2*TRACK_MIN_SPOT_LIMIT)) > (30 + TRACK_WINDOW_SIZE_TOLERANCE) ||
	   abs(window.h - (spotWidth + 2*TRACK_MIN_SPOT_LIMIT)) > (30 + TRACK_WINDOW_SIZE_TOLERANCE) ||
	   spot.x < distanceLimit || spot.x > window.w - distanceLimit ||
	   spot.y < distanceLimit || spot.y > window.h - distanceLimit)
	{
		// Update is most likely needed, calculate new bounds
		int width = spotWidth + 2*TRACK_MIN_SPOT_LIMIT, height = width, temp;
		int x = frame.area.x + spot.x - width/2;
		int y = frame.area.y + spot.y - height/2;

		// Canvas clamping and quantization
		// x and width must be a multiple of 16
		if(x >= 0)
		{
			temp = x % 16;
			x -= temp;
			width += temp;
		}
		else
		{
			width += x;
			x = 0;
		}
		if(width % 16 != 0) width += (16 - (width % 16));

		// y and height must be a multiple of 8
		if(y >= 0)
		{
			temp = y % 8;
			y -= temp;
			height += temp;
		}
		else
		{
			height += y;
			y = 0;
		}
		if(height % 8 != 0) height += (8 - (height % 8));

		// Final check
		if(x != window.x || y != window.y || height != window.h || width != window.w)
		{
			log(std::cout, "Updated window to", width, "x", height, "at [", x, ",", y, "]");
			window.x = x;
			window.y = y;
			window.w = width;
			window.h = height;
		}
	}
}

// Finds group that is most likely the spot we are looking for, based on its last properties
//-----------------------------------------------------------------------------
int Tracking::findSpotCandidate(Image& frame, Group& oldSpot, double *difference)
//-----------------------------------------------------------------------------
{
	int candidate = 0;
	double minDifference = 1e10;

	for(unsigned int i = 0; i < frame.groups.size(); i++)
	{
		double difference;

		// If size uncertain just check position
		if(oldSpot.pixelCount == 0)
		{
			difference = abs(frame.area.x + frame.groups[i].x - oldSpot.x) +
				abs(frame.area.y + frame.groups[i].y - oldSpot.y);
		}
		else
		{
			// Sum size, pixel count and brightness (half weight) offsets
			difference = abs(frame.area.x + frame.groups[i].x - oldSpot.x) +
				abs(frame.area.y + frame.groups[i].y - oldSpot.y) +
				abs((int)frame.groups[i].pixelCount - (int)oldSpot.pixelCount) +
				abs((int)frame.groups[i].valueMax/2 - (int)oldSpot.valueMax/2);
		}

		if(difference < minDifference)
		{
			minDifference = difference;
			candidate = i;
		}
	}

	*difference = minDifference;

	return candidate;
}

// Control FSM in open loop using calibrated projections
//-----------------------------------------------------------------------------
void Tracking::controlOpenLoop(FSM& fsm, double x, double y)
//-----------------------------------------------------------------------------
{
	actionX = calibration.affineTransformX(x, y);
	actionY = calibration.affineTransformY(x, y);
	// log(std::cout, "Moving FSM to", x, y, "... that is", actionX, actionY);
	fsm.setNormalizedAngles(actionX, actionY);
	lastUpdate = steady_clock::now();
}

// Control FSM with feedback to setpoint using integral control
//-----------------------------------------------------------------------------
void Tracking::control(FSM& fsm, double x, double y, double spX, double spY)
//-----------------------------------------------------------------------------
{
	// Calculate elapsed time
	time_point<steady_clock> now = steady_clock::now();
	duration<double> diff = now - lastUpdate;
	double Ts = diff.count() > TRACK_CONTROL_MAX_TS ? TRACK_CONTROL_MAX_TS : diff.count();

	// log(std::cout, "Ts is", diff.count());

	// Calculate errors on FSM
	double ex = calibration.transformDx(spX - x, spY - y);
	double ey = calibration.transformDy(spX - x, spY - y);

	// Calculate integral deltas
	double dxFSM = ex * Ts * TRACK_CONTROL_I;
	double dyFSM = ey * Ts * TRACK_CONTROL_I;
	if(dxFSM > CALIB_FSM_MAX_DELTA) dxFSM = CALIB_FSM_MAX_DELTA;
	if(dyFSM > CALIB_FSM_MAX_DELTA) dyFSM = CALIB_FSM_MAX_DELTA;

	// Anti-windup
	if(abs(actionX + dxFSM) > 1)
	{
		if(actionX + dxFSM > 1) actionX = 1;
		else if(actionX + dxFSM < -1) actionX = -1;
	}
	else actionX += dxFSM;

	if(abs(actionY + dyFSM) > 1)
	{
		if(actionY + dyFSM > 1) actionY = 1;
		else if(actionY + dyFSM < -1) actionY = -1;
	}
	else actionY += dyFSM;

	// Update output
	fsm.setNormalizedAngles(actionX, actionY);
	lastUpdate = now;
}

// Check whether spots are at a safe distance and closed-loop tracking is possible
//-----------------------------------------------------------------------------
bool distanceIsSafe(Group& beacon, Group& calib, bool openloop)
//-----------------------------------------------------------------------------
{
	double distance = sqrt((beacon.x - calib.x)*(beacon.x - calib.x) + 
		(beacon.y - calib.y)*(beacon.y - calib.y));
	if(openloop && distance > TRACK_SAFE_DISTANCE_ALLOW) return true;
	if(!openloop && distance > TRACK_SAFE_DISTANCE_PANIC) return true;
	return false;
}
