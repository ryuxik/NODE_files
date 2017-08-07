## MatrixVision SDK
mvINC = /opt/mvIMPACT_acquire/
mvLIB = /opt/mvIMPACT_acquire/lib/x86_64/

## SocketIO SDK
ioINC = /media/Whatevers/socketio_cpp/build/include/
ioLIB = /media/Whatevers/socketio_cpp/build/lib/Release/

## Compiler/Linker config
CC = g++
CFLAGS = -O2 -std=c++11 -Wall -W -fPIC -D_REENTRANT -pedantic -Wno-format -Wno-unused-parameter -fvisibility=hidden
LIBS = -lmvDeviceManager -lsioclient -lpthread -lboost_system -lpigpiod_if2

## Output
ODIR = .
OBJS = main.o camera.o link.o processing.o fsm.o tracking.o calibration.o
OUT = test

$(ODIR)/%.o: %.cpp
	$(CC) -c -o $@ $< $(CFLAGS) -I$(mvINC) -I$(ioINC)

$(OUT): $(OBJS)
	$(CC) -o $@ $^ $(CFLAGS) -L$(mvLIB) -L$(ioLIB) $(LIBS)

debug: CFLAGS += -DDEBUG -g
debug: $(OUT)

run:
	# ./$(OUT)
	scp main.cpp pi@10.0.5.2:/home/pi/closed_loop/

.PHONY: clean

clean:
	rm -f $(ODIR)/*.o $(OUT)