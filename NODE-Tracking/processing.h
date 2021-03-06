// Image processing classes for beacon detector
// Author: Ondrej Cierny
#ifndef __PROCESSING
#define __PROCESSING
#include <vector>
#include "camera.h"

#define MAX_GROUPS 50					// Failsafe - max allowed pixel groups to process
#define MAX_ACTIVE_PIXELS 100000		// Failsafe - max allowed active pixels in frame
#define MIN_PIXELS_PER_GROUP 5			// Failsafe - minimum, in order to avoid grouping potential hot pixels

#define THRESHOLD_SAFETY_OFFSET 50		// Offset to add to histogram mean for thresholding

using namespace std;

// A group/centroid of active pixels
class Group
{
public:
	double x, y;
	unsigned int valueMax, valueSum, pixelCount;
	Group() : x(0), y(0), valueMax(0), valueSum(0), pixelCount(0) {}

	// Operator overload for sorting
	bool operator < (const Group& other) const
	{
		return valueMax > other.valueMax;
	}
};

// Base image class
class Image
{
	TCameraBinningMode binningMode;
public:
	int size;
	AOI area;
	vector<Group> groups;
	uint16_t *data, histBrightest, histPeak, histMean;
	Image(Camera &camera, int smoothing = 0);
	~Image();
	// Processing functions
	void applyFastBlur(double radius, double passes = 2);
	uint16_t autoThresholdPeakToMax(float fraction = 1.75);
	int performPixelGrouping(uint16_t threshold = 0);
};

#endif
