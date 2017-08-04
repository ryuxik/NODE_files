#include <Python.h>
#include "factorial.h"

static char module_docstring[] =
	"This module provides an interface for calculating factorials using C.";
static char factorial_docstring[] =
	"Calculate the factorial of a given number.";

static PyObject *factorial_factorial(PyObject *self, PyObject *args);

static PyMethodDef module_methods[] = {
	{"factorial", factorial_factorial, METH_VARARGS, factorial_docstring},
	{NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC init_factorial(void)
{
	PyObject *m = Py_InitModule3("_factorial", module_methods, module_docstring);
	if (m == NULL)
		return;
}

static PyObject *factorial_factorial(PyObject *self, PyObject *args)
{
	int X;

	/*Parse the input tuple */
	if (!PyArg_ParseTuple(args, "i", &X))
		return NULL;

	/*Call the external C function to compute the factorial. */
	//Py_BEGIN_ALLOW_THREADS;
	int value = factorial(X);
	//Py_END_ALLOW_THREADS;

	/* Build the output tuple. */
	PyObject *ret = Py_BuildValue("i", value);
	return ret;
}