#include "factorial.h"

long int factorial(int X) {
	int x;
	long int result = 1, intermediate;

	for (x = 1; x <= X; x++) {
		intermediate = result * x;
		result = intermediate;
	}

	return result;
}