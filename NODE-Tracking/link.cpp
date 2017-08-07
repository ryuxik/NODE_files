// Easy GUI communication through socket.IO
// Author: Ondrej Cierny
#include "link.h"
#include "log.h"

//-----------------------------------------------------------------------------
Link::Link(string url)
//-----------------------------------------------------------------------------
{
	connect(url);
	beaconImage = sio::object_message::create();
	calibImage = sio::object_message::create();
	lastUpdate = steady_clock::now();
}

//-----------------------------------------------------------------------------
Link::~Link()
//-----------------------------------------------------------------------------
{
	if(c.opened())
	{
		c.sync_close();
    	c.clear_con_listeners();
    }
}

//-----------------------------------------------------------------------------
void Link::connect(string url)
//-----------------------------------------------------------------------------
{
	if(!c.opened()) c.connect(url);
}

//-----------------------------------------------------------------------------
void Link::on(string cmd, function<void(sio::event&)> callback)
//-----------------------------------------------------------------------------
{
	c.socket()->on(cmd, callback);
}

//-----------------------------------------------------------------------------
void Link::setBeacon(Image& frame)
//-----------------------------------------------------------------------------
{
	setImage(frame, beaconImage);
}

//-----------------------------------------------------------------------------
void Link::setCalib(Image& frame)
//-----------------------------------------------------------------------------
{
	setImage(frame, calibImage);
}

// Send update of all tracking variables and images at a steady FPS
//-----------------------------------------------------------------------------
void Link::sendUpdate(bool bK, bool cK, double bX, double bY, double cX, double cY, double fX, double fY)
//-----------------------------------------------------------------------------
{
	time_point<steady_clock> now = steady_clock::now();
	duration<float> diff = now - lastUpdate;
	if(1.0f / diff.count() < LINK_MAX_FPS)
	{
		lastUpdate = now;
		auto msg = sio::object_message::create();
		msg->get_map()["bK"] = sio::bool_message::create(bK);
		msg->get_map()["cK"] = sio::bool_message::create(cK);
		msg->get_map()["bX"] = sio::double_message::create(bX);
		msg->get_map()["bY"] = sio::double_message::create(bY);
		msg->get_map()["cX"] = sio::double_message::create(cX);
		msg->get_map()["cY"] = sio::double_message::create(cY);
		msg->get_map()["fX"] = sio::double_message::create(fX);
		msg->get_map()["fY"] = sio::double_message::create(fY);
		if(beaconImage->get_map().size() > 0) msg->get_map()["b"] = beaconImage;
		if(calibImage->get_map().size() > 0) msg->get_map()["c"] = calibImage;
		c.socket()->emit("update", msg);
	}
}

// Resize, downsample, generate a BMP frame, construct socketIO object message
//-----------------------------------------------------------------------------
void Link::setImage(Image& frame, sio::message::ptr& local)
//-----------------------------------------------------------------------------
{
	int newHeight = frame.area.h, newWidth = frame.area.w, ratio = 1;
	shared_ptr<string> data = make_shared<string>();

	// Determine if resizing is needed
	if(frame.area.h > LINK_MAX_FRAME_HEIGHT)
	{
		ratio = frame.area.h / LINK_MAX_FRAME_HEIGHT + 1;
		if(ratio == 3 || ratio > 4) ratio = 4;
		newHeight = frame.area.h / ratio;
		newWidth = frame.area.w / ratio;
	}
	
	// Helper frame header generation function
	auto addBytes = [&](int value, int8_t n)
	{
		for(int8_t i = 0; i < n; i++)
		{
			data->append(1, (value >> i*8) & 0xFF);
		}
	};

	// Generate a BMP image header
	addBytes(19778, 2);
	addBytes(1078 + newHeight*newWidth, 4);
	addBytes(0, 4);
	addBytes(1078, 4);
	addBytes(40, 4);
	addBytes(newWidth, 4);
	addBytes(newHeight, 4);
	addBytes(1, 2);
	addBytes(8, 2);
	addBytes(0, 4);
	addBytes(newHeight*newWidth, 4);
	addBytes(2835, 4);
	addBytes(2835, 4);
	addBytes(0, 4);
	addBytes(0, 4);

	// BMP grayscale color palette
	for(int i = 0; i < 256; i++)
	{
		addBytes(i + i*256 + i*65536, 4);
	}

	// Resize, downsample to 8-bit, flip vertically (ref. BMP format)
	switch(ratio)
	{
		case 1:
			for(int i = newHeight - 1; i >= 0; i--)
			{
				for(int j = 0; j < newWidth; j++)
				{
					data->append(1, frame.data[(i*frame.area.w)+j] >> 2);
				}
			}
			break;
		case 2:
			for(int i = newHeight - 1; i >= 0; i--)
			{
				int ii0 = i * frame.area.w * 2;
				int ii1 = ii0 + frame.area.w;
				for(int j = 0; j < newWidth; j++)
				{
					int jj0 = 2 * j;
					int jj1 = jj0 + 1;
					data->append(1, (frame.data[ii0 + jj0] + frame.data[ii0 + jj1] + 
									 frame.data[ii1 + jj0] + frame.data[ii1 + jj1]) >> 4);
				}
			}
			break;
		default:
			for(int i = newHeight - 1; i >= 0; i--)
			{
				int ii0 = i * frame.area.w * 4;
				int ii1 = ii0 + frame.area.w;
				int ii2 = ii1 + frame.area.w;
				int ii3 = ii2 + frame.area.w;
				for(int j = 0; j < newWidth; j++)
				{
					int jj0 = 4 * j;
					int jj1 = jj0 + 1;
					int jj2 = jj1 + 1;
					int jj3 = jj2 + 1;
					data->append(1, (frame.data[ii0 + jj0] + frame.data[ii0 + jj1] +
									 frame.data[ii0 + jj2] + frame.data[ii0 + jj3] +
									 frame.data[ii1 + jj0] + frame.data[ii1 + jj1] +
									 frame.data[ii1 + jj2] + frame.data[ii1 + jj3] +
									 frame.data[ii2 + jj0] + frame.data[ii2 + jj1] +
									 frame.data[ii1 + jj2] + frame.data[ii2 + jj3] +
									 frame.data[ii3 + jj0] + frame.data[ii3 + jj1] +
									 frame.data[ii1 + jj2] + frame.data[ii3 + jj3]) >> 6);
				}
			}
	}
	
	// Remove old stuff
	if(local->get_map().size() > 0)
	{
		local->get_map()["groups"]->get_vector().clear();
		local->get_map().clear();
	}

	// Add new stuff
	local->get_map()["groups"] = sio::array_message::create();
	local->get_map()["data"] = sio::binary_message::create(data);
	for(Group& g : frame.groups)
	{
		auto group = sio::object_message::create();
		group->get_map()["x"] = sio::double_message::create(g.x);
		group->get_map()["y"] = sio::double_message::create(g.y);
		group->get_map()["max"] = sio::int_message::create(g.valueMax);
		group->get_map()["total"] = sio::int_message::create(g.pixelCount);
		local->get_map()["groups"]->get_vector().push_back(group);
	}
}
