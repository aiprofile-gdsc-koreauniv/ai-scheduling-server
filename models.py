from pydantic import BaseModel
from typing import List
from datetime import datetime
from logger import logger
from config import VALID_STATE

class EngineStatus:
    # status: 
    #  -1 : no_response
    #   0 : ready
    #   1 : processing
    def __init__(self, url: str, status: int):
        self.url: str = url
        self.status: int = status
    
    def set_status(self, status: int):
        if status not in VALID_STATE:
            logger.error(f"Error - InvalidStatus - engine:{self.url} - status:{self.status} - recieved: {status}")
            raise Exception("InvalidStatus-Engine")
        self.status = status
    
    def to_json(self):
        return {
            "url": self.url,
            "status": self.status
        }


class Job:
    # status:
    #   0 : pending
    #   1 : processing
    #  -1 : proccessed
    
    def __init__(self, id: str, image_paths: List[str], is_male: bool, is_black: bool, is_blonde: bool, recieved_time: str, dispatched_time:str=None, processed_time:str=None):
        self.id: str = id
        self.image_paths: List[str] = image_paths
        self.is_male: bool = is_male
        self.is_black:bool = is_black
        self.is_blonde: bool = is_blonde
        self.recieved_time: str = recieved_time
        if dispatched_time is None: self.dispatched_time: str = dispatched_time
        else: self.dispatched_time: str = ""
        if processed_time is None: self.processed_time: str = processed_time
        else: self.processed_time: str = ""
    
    def to_json(self):
        return {
            "id": self.id,
            "image_paths": self.image_paths,
            "param": {
                "is_male": self.is_male,
                "is_black": self.is_black,
                "is_blonde": self.is_blonde
            },
            "recieved_time": self.recieved_time,
            "dispatched_time": self.dispatched_time,
            "processed_time": self.processed_time
        }
    
    @classmethod
    def from_json(cls, data):
        return cls(
            id=data["id"],
            image_paths=data["image_paths"],
            is_male=data["param"]["is_male"],
            is_black=data["param"]["is_black"],
            is_blonde=data["param"]["is_blonde"],
            recieved_time=data["recieved_time"],
            dispatched_time=data["dispatched_time"],
            processed_time=data["processed_time"]
        )




class EngineRequest:
    def __init__(self, id: str, is_male:bool, is_black:bool,is_blonde:bool, image_paths: List[str]):
        self.id = id
        self.is_male = is_male
        self.is_black = is_black
        self.is_blonde = is_blonde
        self.image_paths = image_paths

    def to_json(self):
        return {
            "id": self.id,
            "param": {
                "is_male": self.is_male,
                "is_black": self.is_black,
                "is_blonde": self.is_blonde
            },
            "image_paths": self.image_paths
        }

class WASResult:
    def __init__(self, id: str, error: bool, image_paths: List[str]):
        self.id = id
        self.error = error
        self.image_paths = image_paths

    def to_json(self):
        return {
            "id": self.id,
            "imagePaths": self.image_paths,
            "isError": self.error
        }


class ImgParam(BaseModel):
    is_male: bool
    is_blonde: bool
    is_black: bool
    

class JobAddPayload(BaseModel):
    id: str
    param: ImgParam
    imagePaths: List[str]


class EngineListUpdateParam(BaseModel):
    engine_url: str
    
