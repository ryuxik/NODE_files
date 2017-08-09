import multiprocessing
import logging
from log_sort import *
import time
def loggingstuff(lines, words, inputfile):
  logging.basicConfig(format='%(asctime)s|%(message)s:', filename=inputfile , level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S') #sets up logger
  for i in range(lines):
      logging.info(words)
      time.sleep(.5)



if __name__ == "__main__":

    p1 = multiprocessing.Process(target=loggingstuff, args=(10, "hello", "test1.log") )
    p2 = multiprocessing.Process(target=loggingstuff, args=(10, "omg", "test2.log"))

    p1.start()
    p2.start()

    p1.join()
    p2.join()
    log_sort("test1.log", "test2.log")
