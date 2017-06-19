//From http://www.pieter-jan.com/node/15
#include <stdio.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>

#define BCM2837_PERI_BASE 0x20000000
#define GPIO_BASE         (BCM2837_PERI_BASE + 0x200000)
#define BLOCK_SIZE        (4*1024)

//use INP_GPIO() before OUT_GPIO()
#define INP_GPIO(g) *(gpio.addr + ((g)/10)) &= ~(7<<(((g)%10)*3))
#define OUT_GPIO(g) *(gpio.addr + ((g)/10)) |= (1<<(((g)%10)*3))
#define SET_GPIO_ALT(g,a) *(gpio.addr + (((g)/10))) |= (((a)<=3?(a) + 4:(a)==4?3:2)<<(((g)%10)*3))
#define GPIO_SET *(gpio.addr + 7) //sets bits which are 1 ignores 0s
#define GPIO_CLR *(gpio.addr + 10)//clears bits which are 1 ignores 0s
#define GPIO_READ(g) *(gpio.addr + 13) &= (1<<(g))

struct bcm2837_peripheral {
	unsigned long addr_p;
	int mem_fd;
	void *map;
	volatile unsigned int *addr;
};

struct bcm2837_peripheral gpio = {GPIO_BASE};

extern struct bcm2837_peripheral gpio;