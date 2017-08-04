import _factorial
import timeit

def w(func, *args):
	def wr():
		return func(*args)
	return wr

def f(x):
	a = 1
	for i in range(1,x+1):
		a *= i
	return a

if __name__ == '__main__':
	
	h = 15
	for i in range(1, h):
		a = f(i)
		b = _factorial.factorial(i)
		if a != b:
			print a, b, 'at: ',i
			break
	# py = w(f, h)
	# print(timeit.timeit(py, number=1))

	# c = w(_factorial.factorial, h)
	# print(timeit.timeit(c, number=1))