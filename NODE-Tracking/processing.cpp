// Image processing classes for beacon detector
// Author: Ondrej Cierny
#include "processing.h"
#include "log.h"
#include <cmath>
#include <functional>
#include <algorithm>

//-----------------------------------------------------------------------------
Image::Image(Camera &camera, int smoothing)
//-----------------------------------------------------------------------------
{
	// Copy properties
	const Request *request = camera.getRequest();
	binningMode = camera.config->binningMode.read();
	size = request->imageSize.read();
	area.w = request->imageWidth.read();
	area.h = request->imageHeight.read();
	area.x = request->imageOffsetX.read();
	area.y = request->imageOffsetY.read();
	data = new uint16_t[area.w*area.h];
	memcpy(data, request->imageData.read(), size);

	// Unlock camera request
	camera.unlockRequest();

	// Smoothing
	applyFastBlur(smoothing);

	// Basic histogram analysis, find peak and brightest pixel
	int histogram[1024], maxCount = 0, sum = 0;
	memset(histogram, 0, 1024*sizeof(int));
	histBrightest = 0;
	for(int i = 0; i < area.w*area.h; i++)
	{
		if(data[i] > 1023)
		{
			log(std::cerr, "Brightness overflow detected in frame");
			continue;
		}
		sum += data[i];
		histogram[data[i]]++;
		if(histogram[data[i]] > maxCount)
		{
			maxCount = histogram[data[i]];
			histPeak = data[i];
		}
		if(data[i] > histBrightest) histBrightest = data[i];
	}
	histMean = sum / (area.w * area.h);
}

//-----------------------------------------------------------------------------
Image::~Image()
//-----------------------------------------------------------------------------
{
	delete data;
}

// Maps neighboring pixels to groups and performs group centroiding
// TODO: seems to crash sometimes when camera is oversaturated, memory problem?!
//-----------------------------------------------------------------------------
int Image::performPixelGrouping(uint16_t threshold)
//-----------------------------------------------------------------------------
{
	unsigned int currentGroup = 0;
	set<int> groupedPixels;
	groups.clear();

	// Determine thresholding if not given
	// if(threshold == 0) threshold = autoThresholdPeakToMax();
	if(threshold == 0) threshold = histMean + THRESHOLD_SAFETY_OFFSET;

	// Helper recursive group-propagation function
	function<void(int,int)> propagateGroup;
	propagateGroup = [this, threshold, &currentGroup, &groupedPixels, &propagateGroup](int i, int j)
	{
		// Acknowledge parent pixel in group
		int index = i*area.w + j;
		Group& g = groups[currentGroup];
		g.pixelCount++;
		g.valueSum += data[index];
		g.x += j * data[index];
		g.y += i * data[index];
		if(data[index] > g.valueMax) g.valueMax = data[index];
		groupedPixels.insert(index);

		// Fail-safe
		if(groupedPixels.size() > MAX_ACTIVE_PIXELS) return;

		// Loop through neighbors
		for(int8_t x = -1; x <= 1; x++)
		{
			for(int8_t y = -1; y <= 1; y++)
			{
				if((i+x) >= 0 && (i+x) < area.h && (j+y) >= 0 && (j+y) < area.w)
				{
					index = (i+x)*area.w + j + y;
					if(groupedPixels.count(index) == 0 && data[index] > threshold)
					{
						propagateGroup(i+x, j+y);
					}
				}
			}
		}
	};

	// Scan all pixels
	for(int i = 0; i < area.h; i++)
	{
		for(int j = 0; j < area.w; j++)
		{
			int index = i*area.w + j;
			if(data[index] > threshold && groupedPixels.count(index) == 0)
			{
				// Ungrouped pixel found, propagate a new group
				groups.emplace_back();
				propagateGroup(i, j);

				// Verify number of pixels in group after propagation
				if(groups[currentGroup].pixelCount < MIN_PIXELS_PER_GROUP)
				{
					groups.pop_back();
					continue;
				}

				// Too many active pixels, must be background, clear and return
				if(groupedPixels.size() > MAX_ACTIVE_PIXELS)
				{
					log(std::cerr, "Frame has too many active pixels!");
					groups.clear();
					return -1;
				}

				// Calculate centroid for group
				groups[currentGroup].x /= groups[currentGroup].valueSum;
				groups[currentGroup].y /= groups[currentGroup].valueSum;

				// Increase and check group count
				if(++currentGroup > MAX_GROUPS)
				{
					log(std::cerr, "Frame has too many groups!");
					sort(groups.begin(), groups.end());
					return -1;
				}
			}
		}
	}

	// Sort max-brightness-descending
	if(groups.size() > 0) sort(groups.begin(), groups.end());
	else log(std::cerr, "Frame has no groups!");

	return groups.size();
}

// Super-fast box blur algorithm, converges to Gaussian with more passes
// Adapted from: http://blog.ivank.net/fastest-gaussian-blur.html
//-----------------------------------------------------------------------------
void Image::applyFastBlur(double radius, double passes)
//-----------------------------------------------------------------------------
{
	if(radius < 1) return;
	uint16_t *temp = new uint16_t[area.w*area.h];
	memcpy(temp, data, size);

	// Calculate boxes area.w
	int wl = sqrt((12*radius*radius/passes)+1);
	if(wl % 2 == 0) wl--;
	int m = ((12*radius*radius - passes*wl*wl - 4*passes*wl - 3*passes)/(-4*wl - 4)) + 0.5f;

	// Blur for n passes
	for(int8_t n = 0; n < passes; n++)
	{
		int r = ((n < m ? wl : wl + 2) - 1) / 2;
		float iarr = 1.0f / (r+r+1);

		// Apply horizontal blur
		for(int i = 0; i < area.h; i++)
		{
			int ti = i*area.w, li = ti, ri = ti + r;
			int fv = data[ti], lv = data[ti+area.w-1], val = (r+1)*fv;
			for(int j = 0; j < r; j++) val += data[ti+j];
			for(int j = 0; j <= r; j++) { val += data[ri++] - fv; temp[ti++] = val*iarr + 0.5f; }
			for(int j = r+1; j < area.w-r; j++) { val += data[ri++] - data[li++]; temp[ti++] = val*iarr + 0.5f; }
			for(int j = area.w-r; j < area.w; j++) { val += lv - data[li++]; temp[ti++] = val*iarr + 0.5f; }
		}
		memcpy(data, temp, size);

		// Apply total blur
		for(int i = 0; i < area.w; i++)
		{
			int ti = i, li = ti, ri = ti + r*area.w;
			int fv = data[ti], lv = data[ti + area.w*(area.h-1)], val = (r+1)*fv;
			for(int j = 0; j < r; j++) val += data[ti + j*area.w];
			for(int j = 0; j <= r; j++) { val += data[ri] - fv; temp[ti] = val*iarr + 0.5f; ri += area.w; ti += area.w; }
			for(int j = r+1; j < area.h-r; j++) { val += data[ri] - data[li]; temp[ti] = val*iarr + 0.5f; li += area.w; ri += area.w; ti += area.w; }
			for(int j = area.h-r; j < area.h; j++) { val += lv - data[li]; temp[ti] = val*iarr + 0.5f; li += area.w; ti += area.w; }
		}
		memcpy(data, temp, size);
	}

	delete temp;
}

// Threshold as a fraction of distance between histogram peak and max brightness
//-----------------------------------------------------------------------------
uint16_t Image::autoThresholdPeakToMax(float fraction)
//-----------------------------------------------------------------------------
{
	int treshold = 1023;
	if(histBrightest > histPeak)
	{
		treshold = histPeak + ((histBrightest - histPeak) / fraction);
	}		
	return treshold;
}
