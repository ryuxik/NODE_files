import logging
import time

logging.basicConfig(format='%(asctime)s|%(message)s:', filename='test1.log', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S') #sets up logger
for i in range(10):
    logging.info("hello")
    
