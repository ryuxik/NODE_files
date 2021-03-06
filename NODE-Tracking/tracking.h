// NODE Tracking algorithms
// Author: Ondrej Cierny
#ifndef __TRACKING
#define __TRACKING
#include <chrono>
#include "camera.h"
#include "processing.h"
#include "calibration.h"

#define TRACK_MIN_EXPOSURE 1000

#define TRACK_ACQUISITION_BRIGHTNESS 300		// Minimum spot brightness to work with for acquisition
#define TRACK_ACQUISITION_WINDOW 200			// Initial camera window size after acquisition is declared
#define TRACK_GOOD_PEAKTOMAX_DISTANCE 100		// Minimum distance between histogram peak's brightness and maximum brightness
												// I.e. difference between most pixels (background) and active (brightest) pixels

#define TRACK_HAPPY_BRIGHTNESS 700				// Good brightness for auto exposure tuning
#define TRACK_SATURATION_LIMIT 990				// Camera is hard-saturated at around 990 brightness

#define TRACK_TUNING_MAX_ATTEMPTS 10			// Failsafe - give up tuning after 10 incorrect attempts (tuning noise?)
#define TRACK_TUNING_TOLERANCE 50				// Distance from TRACK_HAPPY_BRIGHTNESS that we are still happy with
#define TRACK_TUNING_POSITION_TOLERANCE 2		// Tolerance in location of spot in-between two tuning frames (jitter)
#define TRACK_TUNING_BRIGHTNESS_TOLERANCE 20	// Tolerance in brightness of spot in-between two tuning frames (jitter)
#define TRACK_TUNING_EXP_DIVIDER 12				// Exposure tuning division factor, the higher the finer tuning, but slower

#define TRACK_WINDOW_SIZE_TOLERANCE 10			// If tracking window differs by more than this we definitely want an update
#define TRACK_MAX_SPOT_DIFFERENCE 60			// If spot parameters changed by too much since last update, something's wrong
#define TRACK_MIN_SPOT_LIMIT 25					// Minimum distance from spot to edge of adaptive window, i.e. assure safe distances

#define TRACK_CONTROL_I 40						// Controller integral constant
#define TRACK_CONTROL_MAX_TS 0.05f				// Max Ts to allow, prevent controller going crazy when out-of-sync

#define TRACK_SAFE_DISTANCE_ALLOW 200
#define TRACK_SAFE_DISTANCE_PANIC 100

using namespace std::chrono;

class Tracking
{
	Camera& camera;
	Calibration& calibration;
	time_point<steady_clock> lastUpdate;
	bool verifyFrame(Image& frame);
	bool windowAndTune(Image& frame, Group& beacon);
	bool autoTuneExposure(Group& beacon);
public:
	int beaconSmoothing;
	double actionX, actionY;
	Tracking(Camera& c, Calibration& calib) : camera(c), calibration(calib), beaconSmoothing(0), actionX(0), actionY(0) {}
	bool runAcquisition(Group& beacon);
	int findSpotCandidate(Image& frame, Group& oldSpot, double *difference);
	void updateTrackingWindow(Image& frame, Group& spot, AOI& window);
	void control(FSM& fsm, double x, double y, double spX, double spY);
	void controlOpenLoop(FSM& fsm, double x, double y);
	bool distanceIsSafe(Group& beacon, Group& calib, bool openloop);
};

#endif
