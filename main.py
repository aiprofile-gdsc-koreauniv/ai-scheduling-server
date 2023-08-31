from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import time
import uvicorn
from datetime import datetime
import asyncio
import random

app = FastAPI()

scheduler = AsyncIOScheduler(job_defaults={'max_instances': 3})

cnt= 0

async def print_hello_world():
    global cnt
    id = random.randint(0, 10000)
    time_str = datetime.now().strftime("%H:%M:%S")
    print(f"id:{id:06d} : {time_str}")
    await asyncio.sleep(6)
    time_str = datetime.now().strftime("%H:%M:%S")
    print(f"id:{id:06d} : {time_str}")
    cnt += 1

async def print_hello_world_asd():
    time_str = datetime.now().strftime("%H:%M:%S")
    print(f"2222len:{cnt} : {time_str}")

# Stop the scheduler when the app stops
@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    
@app.get("/test")
async def asd():
    print("test recieved")
    time.sleep(10)
    return {"status":"done"}

@app.get("/")
async def qwe():
    print("status recieved")
    return {"status":"done"}

# scheduler.add_job(print_hello_world_asd, 'interval', seconds=2)
scheduler.add_job(print_hello_world, 'interval', seconds=2)
scheduler.start()

if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
