import logging
from os import makedirs, path

# ensure that the logs directory exists
if not path.isdir('logs'):
    makedirs('logs')

logger = logging.getLogger('scraper_runtime')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create file handler and set level to debug
fh = logging.FileHandler('logs/scraper_runtime.log')

# create formatter
formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(message)s')

# add formatter to ch
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# add handlers to logger
logger.addHandler(ch)
logger.addHandler(fh)
