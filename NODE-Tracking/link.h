// Easy GUI communication through socket.IO
// Author: Ondrej Cierny
#ifndef __LINK
#define __LINK
#include "sio_client.h"
#include <chrono>
#include "processing.h"

#define LINK_MAX_FRAME_HEIGHT 640
#define LINK_MAX_FPS 15

using namespace std;
using namespace std::chrono;

class Link
{
	sio::client c;
	time_point<steady_clock> lastUpdate;
	sio::message::ptr beaconImage, calibImage;
	void setImage(Image& frame, sio::message::ptr& local);
public:
	Link(string url);
	~Link();
	void connect(string url);
	void on(string cmd, function<void(sio::event&)> callback);
	void setBeacon(Image& frame);
	void setCalib(Image& frame);
	void sendUpdate(bool bK, bool cK, double bX, double bY, double cX, double cY, double fX, double fY);
};

#endif
