// BlueFox camera wrapper class
// Author: Ondrej Cierny
#ifndef __CAMERA
#define __CAMERA
#include "mvIMPACT_CPP/mvIMPACT_acquire.h"

#define CAMERA_WIDTH 2592
#define CAMERA_HEIGHT 1944
#define CAMERA_MAX_WAIT 5000	// Max frame timeout in ms

// An area of interest on camera
class AOI
{
public:
	int x, y, w, h;
	AOI() : x(0), y(0), w(CAMERA_WIDTH), h(CAMERA_HEIGHT) {}
};

// Base camera class
class Camera
{
	int frameId;
	Device *device;
	DeviceManager manager;
	FunctionInterface *fi;
public:
	std::string error;
	int requestQueueSize, queuedCount;
	CameraSettingsBlueFOX *config;
	Camera(std::string serialNumber = "297");
	~Camera();
	bool requestFrame();
	bool waitForFrame();
	bool fillRequestQueue();
	void clearRequestQueue();
	void ignoreNextFrames(int n = 1);
	void unlockRequest();
	void setFullWindow();
	void setWindow(AOI& window);
	void setCenteredWindow(int x, int y, int w);
	const Request* getRequest();
};

#endif
