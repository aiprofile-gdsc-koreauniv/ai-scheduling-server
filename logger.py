import logging 
from config import LOG_PATH


# @@ Logging ############################
logging.getLogger('apscheduler.scheduler').setLevel(logging.ERROR)
logging.getLogger('apscheduler.executors.default').propagate = False
logging.basicConfig(level=logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.FileHandler(LOG_PATH, mode="a")
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
