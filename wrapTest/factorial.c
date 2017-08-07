#include "factorial.h"

int factorial(int X) {
	int x;
	long long int result = 1, intermediate;

	for (x = 1; x <= X; x++) {
		intermediate = result * x;
		result = intermediate;
	}

	printf("%llu", result);
	return 0;
}