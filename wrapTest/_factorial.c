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
	if (!PyArg_ParseTuple(args, "l", &X))
		return NULL;

	/*Call the external C function to compute the factorial. */
	Py_BEGIN_ALLOW_THREADS;
	factorial(X);
	Py_END_ALLOW_THREADS;
	PyObject *ret = Py_BuildValue("i", 0);
	return ret;
}