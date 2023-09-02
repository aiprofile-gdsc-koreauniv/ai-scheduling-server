from dotenv import load_dotenv
import json
import os

load_dotenv()

LOG_PATH = "scheduler.log"
ENGINE_URLS = json.loads(os.environ['ENGINE_URLS'])
VALID_STATE = [-1, 0, 1]
ENGINE_STATUS_TIMEOUT = 20
ENGINE_PROCESS_TIMEOUT = 500
WAS_API_BASE_URL = os.environ['WAS_API_BASE_URL']
VALID_JOB_STATE_STR = ["pending", "in_process", "processed", "error"]