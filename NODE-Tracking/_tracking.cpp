#include <Python.h>

#include <unistd.h>
#include <atomic>
#include <csignal>
#include <chrono>
#include <thread>
#include "pigpiod_if2.h"

#include "log.h"
#include "fsm.h"
#include "camera.h"
#include "processing.h"
#include "tracking.h"
#include "calibration.h"
#include "link.h"

atomic<bool> stop(false);

static char module_docstring[] =
	"This module provides an interface for the NODE-Tracking algorithm.";
static char main_docstring[] =
	"Execute the tracking algorithm.";

static PyObject *main_tracking(PyObject *self, PyObject *args);

static PyMethodDef module_methods[] = {
	{"main", main_tracking, METH_VARARGS, main_docstring},
	{NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC init_tracking(void)
{
	PyObject *m = Py_InitModule3("_tracking", module_methods, module_docstring);
	if (m == NULL)
		return;
}

static PyObject *main_tracking(PyObject *self, PyObject *args)
{
	//Need to implement threading somehow
	result = main();
	PyObject *ret = Py_BuildValue("i", result);
	return ret;
}