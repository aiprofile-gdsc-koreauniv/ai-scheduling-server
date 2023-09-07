# ai-scheduling-server
Scheduling server for scheduling ai-profile generation jobs 

Restores and Synchronizes job scheduling state via `schedule_state.json` file. (which is created at initial run)

Supports job status retrieval & engine status(ai-server) configuration by REST-API at runtime.

## Architecture
```mermaid
flowchart TD
    A[Client] -->|Job| C{Scheduler}
    C -->|Job| D[Engine1]
    C -->|Job| E[Engine2]
    C -->|Job| F[Engine3]
```

## Job sequence
```mermaid
sequenceDiagram
    Scheduler->>+Engine: Healthcheck
    Engine->>-Scheduler: Healthcheck reponse
    Scheduler->>+Engine: Job Request
    Engine->>+Model: Preprocess & Inference Request
    Model-->>-Engine: Result | Error
    Engine-->>+GCP: Result upload
    Engine-->>-Scheduler: Response
```
## State Transfer
### Job State
```mermaid
stateDiagram-v2
    Pending --> InProcess
    InProcess --> Processed
    InProcess --> Error
```
### EngineStatus State
```mermaid
stateDiagram-v2
    Ready --> InProcess
    InProcess --> Ready
    InProcess --> Error
    Error --> Ready
    Ready --> Error
```
## 1. Build&Run
```bash
# git clone prequisites
git clone https://github.com/aiprofile-gdsc-koreauniv/ai-scheduling-server/

cd ai-scheduling-server/

# create error log
touch $PWD/error.txt

# build docker image
docker build -t MY_CONTAINER_NAME .

# docker run
docker run -d \
   -p MY_PORT:9000 \
   -v $PWD:/app \
   MY_CONTAINER_NAME
```



## 참고사항
- docs-url : `http://localhost:MY_PORT/docs` 
- engine : [ai-api-server](https://github.com/aiprofile-gdsc-koreauniv/ai-api-server) 를 의미합니다.
- job : docs에 정의되어 있는 프로필 생성 요청 1건을 의미합니다.
- schedule_state.json : job의 state를 기록/복원하는 state 파일입니다.