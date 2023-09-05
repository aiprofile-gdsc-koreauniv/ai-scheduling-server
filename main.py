from fastapi import FastAPI
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_ERROR
import uvicorn
from datetime import datetime
import asyncio
from logger import logger
from config import ENGINE_URLS, ENGINE_PROCESS_TIMEOUT, ENGINE_STATUS_TIMEOUT, WAS_API_BASE_URL, VALID_JOB_STATE_STR
import requests
from models import EngineListUpdateParam, EngineStatus, EngineRequest, JobAddPayload, WASResult, Job
import httpx
from typing import List, Dict
import os
import json
import copy


app = FastAPI(
    title="AI-Profile-Scheduler-Server",
    description="ai-profile 프로젝트의 AI-Scheduler Server입니다.\n\n 서비스 URL: [호랑이 사진관](https://horangstudio.com)",
    contact={
        "name": "Kyumin Kim",
        "email": "dev.kyoomin@gmail.com",
    },
)

scheduler = AsyncIOScheduler(job_defaults={'max_instances': 3})

time_str = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
engine_list: List[EngineStatus] = []
job_state: Dict[str, List[Job]] = {"datetime": time_str,"pending": [], "in_process": [], "processed": [], "error": []}

default_job_state = {"datetime": "","pending": [], "in_process": [], "processed": [], "error": []}


# TODO :
#   - POST Job O
#   - GET EngineList O
#   - GET EngineListCheck O
#   - PATCH EngineList 
#   - GET StateAll O
#   - GET PendingList O
#   - GET InProcessList O
#   - Gey ErrorList O
#   - GET State-Sync O
#   - Main Loop O 
#   - DockerFile
#   - Update Engine
#   - DELETE job


def on_start():
    # Sync State
    syncJobStateFile()
    
    # Engine State Check
    syncInitEngineStatus()
    logger.info(f"************* Scheduler Start *************")
    return


def writeErrorList(id:str, detail:str):
    time_str = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    with open("error.txt", "a") as file:
        file.write(f"{time_str} id:{id} detail:{detail}\n")


def syncJobStateFile():
    global job_state
    # Check if job_state.json exists
    if os.path.exists("schedule_state.json"):
        # If it exists, load it into the job_state variable
        with open("schedule_state.json", "r") as file:
            tmp_state = json.load(file)
            for state_str in VALID_JOB_STATE_STR:
                for job_json in tmp_state[state_str]:
                    job_state[state_str].append(Job.from_json(job_json))
            job_state["datetime"] = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    else:
        # If it doesn't exist, create it with the default structure
        with open("schedule_state.json", "w") as file:
            tmp_state = copy.deepcopy(default_job_state)
            tmp_state["datetime"] = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
            json.dump(tmp_state, file, indent=4)
    return


def saveJobStateFile():
    global job_state
    time_str = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    job_state["datetime"] = time_str
    with open("schedule_state.json", "w") as file:
        tmp_state = copy.deepcopy(default_job_state)
        for state_str in VALID_JOB_STATE_STR:
            for job in job_state[state_str]:
                tmp_state[state_str].append(job.to_json())
        json.dump(tmp_state, file, indent=4)
    logger.info(f"State-Saved: - {time_str}")


def syncInitEngineStatus():
    global engine_list
    engine_list = [EngineStatus(url=url, status=-1) for url in ENGINE_URLS]
    cnt = 0
    for idx, engine in  enumerate(engine_list):
        logger.info(f"Init-EngineCheck:{engine.url} - status: Connecting...")
        try:
            response = requests.get(f"{engine.url}/api/status", timeout=ENGINE_STATUS_TIMEOUT)
            if response.status_code // 100 == 2:
                cnt += 1
                engine.set_status(0)
                logger.info(f"Init-EngineCheck:{engine.url} - status: CONNECTED")
            else:
                logger.error(f"Init-EngineCheck:{engine.url} - status: NO_CONNECTION")
        except :
            logger.error(f"Init-EngineCheck:{engine.url} - status: ERROR")
    logger.info(f"Init-EngineCheck - Done: {cnt}/{len(engine_list)} available")


def getAvailableEngine() -> EngineStatus | None:
    global engine_list
    for idx, engine in enumerate(engine_list):
        if engine.status == 0:
            return engine
    return None


def syncCheckEngineStatus(engine)->bool:
    try:
        response = requests.get(f"{engine.url}/api/status", timeout=ENGINE_STATUS_TIMEOUT)
        if response.status_code // 100 == 2:
            # logger.info(f"EngineCheck - BeforeProcess :{engine.url} - status: CONNECTED")
            return True
    except:
        pass
    logger.error(f"EngineCheck - BeforeProcess :{engine.url} - status: NO_CONNECTION")
    return False


async def dispatch_job():
    try:
        global job_state
        if len(job_state["pending"]) == 0:
            return
        
        engine = getAvailableEngine()
        if engine is None:
            return
        
        is_checked = syncCheckEngineStatus(engine)
        if not is_checked:
            return
        
        # Engine State Transfer
        engine.set_status(1)
        
        # Job State Transfer
        job = job_state["pending"].pop(0)
        job_state["in_process"].append(job)
        job.dispatched_time = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        
        # Process Job-EngineRequest
        logger.info(f"Job:{job.id} dispatched to {engine.url} - {job.dispatched_time}")
        engine_request_payload = EngineRequest(id=job.id, is_male=job.is_male,is_black=job.is_black, is_blonde=job.is_blonde, image_paths=job.image_paths)
        is_succ, engine_response = await requestPostAsync(url=f"{engine.url}/api/img/process", payload=engine_request_payload.to_json(), headers={"id":job.id}, timeout=ENGINE_PROCESS_TIMEOUT)
        
        
        # Job proccessed time
        job.processed_time = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        if is_succ:
            # Job State Transfer
            job_state["in_process"].remove(job)
            job_state["processed"].append(job)
            payloadResult = WASResult(id=engine_response["id"], error=False, image_paths=engine_response["image_paths"])
            logger.info(f"Job:{job.id} engine processed - {job.processed_time}")
        else:
            # Job State Transfer
            job_state["in_process"].remove(job)
            job_state["error"].append(job)
            payloadResult = WASResult(id=job.id, error=True, image_paths=[])
            logger.error(f"Job:{job.id} engine ERROR - {job.processed_time} {engine.url}")
            requests.post("https://ntfy.sh/horangstudio-scheduler",
                data=f"Job:{job.id} engine ERROR\ndate:{job.processed_time} 🔥\ndetail: EngineFail".encode(encoding='utf-8'))
            
            
        # Engine State Transfer
        engine.set_status(0)
        
        # WAS Result
        is_succ, was_response = await requestPostAsync(url=f"{WAS_API_BASE_URL}/i2i/result", payload=payloadResult.to_json(), timeout=ENGINE_STATUS_TIMEOUT, checkBody=False)
        if not is_succ:
            time_str = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
            logger.error(f"Job:{job.id}  WAS ERROR - {time_str}")
            writeErrorList(job.id, "WAS_FAIL")
        
        # Remove Job from error if re-requested
        removeJobByList(findAllJobById(job_state["error"], job), "error")
        
        logger.info(f"Job:{job.id} Done!")
        requests.post("https://ntfy.sh/horangstudio-approval",
                data=f"처리 완료 id:{job.id} 👍👍 \ndate:{time_str}".encode(encoding='utf-8'))
    except:
        # EngineStateTransfer
        engine.set_status(0)
        
        # JobStateTransfer
        dangling_job = False
        pendingDuplicatedJobList = findAllJobById(job_state["pending"], job)
        in_processDuplicatedJobList = findAllJobById(job_state["in_process"], job)
        
        if len(pendingDuplicatedJobList) != 0:
            removeJobByList(pendingDuplicatedJobList, "pending")
        if len(in_processDuplicatedJobList) != 0:
            removeJobByList(in_processDuplicatedJobList, "in_process")
            
        if len(in_processDuplicatedJobList) == 0 and len(pendingDuplicatedJobList) == 0:
            dangling_job = True
        
        # If dangling
        if dangling_job:
            writeErrorList(job.id, "DANGLING")
        else:
            writeErrorList(job.id, "ERROR")
        
        # JobStateTransfer to error
        if len(findAllJobById(job_state["error"], job)) == 0:
            job_state["error"].append(job)
        
        # Notify
        time_str = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        requests.post("https://ntfy.sh/horangstudio-scheduler",
            data=f"Job:{job.id} 🔥🔥🔥\ndate:{time_str} 🔥".encode(encoding='utf-8'))
        return


def findAllJobById(job_list: List[Job], target_job: Job)-> List[Job]:
    result = []
    for job_ in job_list:
        if job_.id == target_job.id:
            result.append(job_)
    return result


def removeJobByList(target_list: List[Job], state_str: str):
    if state_str not in VALID_JOB_STATE_STR:
        logger.error(f"Error: InvalidState str {state_str} in removing")
        return
    for target_job in target_list:
        job_state[state_str].remove(target_job)


async def requestPostAsync(url: str, payload, headers=None, timeout: int=None, checkBody:bool = True):
    async with httpx.AsyncClient() as client:
        try:
            # Send async POST request to the external API
            response = await client.post(url, json=payload, timeout=httpx.Timeout(timeout), headers=headers)

            # Check if the request was successful (status code 200)
            if checkBody:
                if response.status_code // 100 == 2:
                    data = response.json()  # Parse JSON response
                    return (True, data)
                else:
                    logger.error(f"Error - POST - url: {url} - detail: {response.json()}")
                    return (False, response.json())
            else:
                if response.status_code // 100 == 2:
                    return (True, None)
                else:
                    logger.error(f"Error - POST - url: {url} - detail: {response.json()}")
                    return (False, None)
        except httpx.RequestError as e:
            logger.error(f"Error - POST - url: {url} - detail: {e}")
            return (False, e)
        except:
            logger.error(f"Error - POST - url: {url} - detail: Unknown")
            return (False, None)


async def requestGetAsync(url: str, timeout: int = None):
    async with httpx.AsyncClient() as client:
        try:
            # Send async GET request to the external API
            response = await client.get(url, timeout=httpx.Timeout(timeout))

            # Check if the request was successful (status code 200)
            if response.status_code // 100 == 2:
                data = response.json()  # Parse JSON response
                return (True, data)
            else:
                return (False, None)
        except httpx.RequestError as e:
            return (False, e)
        except:
            logger.error(f"Error - GET - url: {url} - detail: Unknown")
            return (False, None)



@app.get("/health")
async def health_check():
    time_str = datetime.now().strftime("%H:%M:%S")
    return {"status": 200, "time": time_str }


@app.get("/api/engine")
async def getEngineList():
    global engine_list
    cnt = 0
    for engine in engine_list:
        if engine.status == 0:
            cnt += 1
    return JSONResponse(
            status_code=200,
            content={"datetime": time_str,
                     "available_engine":cnt,
                     "all_engine": len(engine_list),
                     "detail": [engine.to_json() for engine in engine_list]}
        )


@app.get("/api/engine/update")
async def syncUpdateAllEngineStatus():
    global engine_list
    cnt = 0
    for engine in engine_list:
        (is_succ, response) = await requestGetAsync(f"{engine.url}/api/status", timeout=ENGINE_STATUS_TIMEOUT)
        if is_succ:
            cnt += 1
            engine.set_status(0)
            logger.info(f"API-EngineCheck:{engine.url} - status: CONNECTED")
        else:
            engine.set_status(-1)
            logger.error(f"API-EngineCheck:{engine.url} - status: NO_CONNECTION")
    return JSONResponse(
            status_code=200,
            content={"datetime": time_str,
                     "available":cnt,
                     "all": len(engine_list),
                     "detail": [engine.to_json() for engine in engine_list]}
        )


@app.patch("/api/engine")
def updateEngineList(item: EngineListUpdateParam):
    try:
        response = requests.get(f"{item.engine_url}/api/status", timeout=ENGINE_STATUS_TIMEOUT)
        if response.status_code // 100 == 2:
            engine = EngineStatus(url=item.engine_url, status=0)
            engine_list.append(engine)
            logger.info(f"New-EngineCheck:{engine.url} - status: CONNECTED")
        else:
            logger.error(f"New-EngineCheck:{item.engine_url} - status: NO_CONNECTION")
    except :
        logger.error(f"Init-EngineCheck:{item.engine_url} - status: ERROR")
    return JSONResponse(
            status_code=200,
            content={"datetime": time_str,
                     "engine_list": len(engine_list),
                     "detail": [engine.to_json() for engine in engine_list]})


@app.get("/api/job/sync")
async def getJobState():
    saveJobStateFile()
    return JSONResponse(
            status_code=200,
            content={"datetime": datetime.now().strftime("%Y-%m-%d-%H:%M:%S"),
                     "message" : "sync done",
                     "pending": len(job_state["pending"]),
                     "in_process": len(job_state["in_process"]), 
                     "processed": len(job_state["processed"]), 
                     "error":  len(job_state["error"]),
                     "detail": "Synced JobState"}
        )


@app.get("/api/job")
async def getJobState():
    global job_state
    tmp_state = copy.deepcopy(default_job_state)
    tmp_state["datetime"] = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    for state_str in VALID_JOB_STATE_STR:
        for job in job_state[state_str]:
            tmp_state[state_str].append(job.to_json())
    return JSONResponse(
            status_code=200,
            content={"datetime": tmp_state["datetime"],
                     "pending": len(job_state["pending"]),
                     "in_process": len(job_state["in_process"]), 
                     "processed": len(job_state["processed"]), 
                     "error":  len(job_state["error"]),
                     "detail": tmp_state}
        )


@app.get("/api/job/pending")
async def getJobStatePending():
    global job_state
    return JSONResponse(
            status_code=200,
            content={"datetime": datetime.now().strftime("%Y-%m-%d-%H:%M:%S"),
                     "pending": len(job_state["pending"]),
                     "detail": [job.to_json() for job in job_state["pending"]]
                     }
        )


@app.get("/api/job/in_process")
async def getJobStateInProcess():
    global job_state
    return JSONResponse(
            status_code=200,
            content={"datetime": datetime.now().strftime("%Y-%m-%d-%H:%M:%S"),
                     "in_process": len(job_state["in_process"]),
                     "detail": [job.to_json() for job in job_state["in_process"]]
                     }
        )


@app.get("/api/job/processed")
async def getJobStateProcessed():
    global job_state
    return JSONResponse(
            status_code=200,
            content={"datetime": datetime.now().strftime("%Y-%m-%d-%H:%M:%S"),
                     "processed": len(job_state["processed"]),
                     "detail": [job.to_json() for job in job_state["processed"]]
                     }
        )


@app.get("/api/job/error")
async def getJobStateError():
    global job_state
    return JSONResponse(
            status_code=200,
            content={"datetime": datetime.now().strftime("%Y-%m-%d-%H:%M:%S"),
                     "processed": len(job_state["error"]),
                     "detail": [job.to_json() for job in job_state["error"]]
                     }
        )


@app.post("/api/job")
async def appendNewJob(item: JobAddPayload):
    new_job = Job(id=item.id, image_paths=item.imagePaths, is_male=item.param.is_male, is_black=item.param.is_black, is_blonde=item.param.is_blonde, recieved_time=datetime.now().strftime("%Y-%m-%d-%H:%M:%S"))
    time_str = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    logger.info(f"Job: {new_job.id} recieved - {time_str}")
    job_state["pending"].append(new_job)
    return JSONResponse(
            status_code=200,
            content={
                     "status": 200,
                     "id": item.id,
                     "pending": len(job_state["pending"]),
                     "datetime": time_str,
            }
        )

def handle_job_exception(event):
    # TODO : Notification
    exception = event.exception
    saveJobStateFile()
    time_str = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    requests.post("https://ntfy.sh/horangstudio-scheduler",
            data=f"Scheduler shutdown 🔥🔥🔥\n {time_str}🔥".encode(encoding='utf-8'))
    logger.error(f"**************SCHEDULER-JOB-EXCEPTION!*************")
    logger.error(f"An exception occurred while executing job {event}: {exception}")
    logger.error(f"***************************************************")

# Stop the scheduler when the app stops
@app.on_event("shutdown")
async def shutdown_event():
    saveJobStateFile()
    scheduler.shutdown()

on_start()
scheduler.add_listener(handle_job_exception, EVENT_JOB_ERROR)
scheduler.add_job(dispatch_job, 'interval', seconds=5)
scheduler.start()

if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

