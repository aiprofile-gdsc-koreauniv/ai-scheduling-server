# ai-scheduling-server
Scheduling server for scheduling ai-profile generation jobs 


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
docs-url : `http://localhost:MY_PORT/docs`