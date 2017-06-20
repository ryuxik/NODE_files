//From http://www.pieter-jan.com/node/15
#include "rpi.h"
#include "rpi.c"
//example code that would blink an led using pin 7 which is gpio 4, 
//refer to pinout to select a pin in general

/*int main(
{
  if(map_peripheral(&gpio) == -1) 
  {
    printf("Failed to map the physical GPIO registers into the virtual memory space.\n");
    return -1;
  }
 
  // Define pin 7 as output
  INP_GPIO(4);
  OUT_GPIO(4);
 
  while(1)
  {
    // Toggle pin 7 (blink a led!)
    GPIO_SET = 1 << 4;
    sleep(1);
 
    GPIO_CLR = 1 << 4;
    sleep(1);
  }
 
  return 0; 
}*/
//Testing code below, not sure if it works
int makeGPIOoutput(int);
int makeGPIOinput(int);
int clearGPIOpin(int);
int setGPIOpinHigh(int);
int setGPIOpinLow(int);

int makeGPIOoutput(int pin)
{
  if(map_peripheral(&gpio) == -1) 
  {
    printf("Failed to map the physical GPIO registers into the virtual memory space.\n");
    return -1;
  }

  INP_GPIO(pin);
  OUT_GPIO(pin);
  return 0;
}

int makeGPIOinput(int pin)
{
  if(map_peripheral(&gpio) == -1) 
  {
    printf("Failed to map the physical GPIO registers into the virtual memory space.\n");
    return -1;
  }

  INP_GPIO(pin);
  return 0;
}

int clearGPIOpin(int pin)
{
  if(map_peripheral(&gpio) == -1) 
  {
    printf("Failed to map the physical GPIO registers into the virtual memory space.\n");
    return -1;
  }

  
  GPIO_CLR = 1 << pin
  return 0;
}

int setGPIOpinHigh(int pin)
{
  if(map_peripheral(&gpio) == -1) 
  {
    printf("Failed to map the physical GPIO registers into the virtual memory space.\n");
    return -1;
  }

  GPIO_SET = 1 << pin
  return 0;
}

int setGPIOpinLow(int pin)
{
  if(map_peripheral(&gpio) == -1) 
  {
    printf("Failed to map the physical GPIO registers into the virtual memory space.\n");
    return -1;
  }

  GPIO_CLR = 1 << pin
  return 0;
}
