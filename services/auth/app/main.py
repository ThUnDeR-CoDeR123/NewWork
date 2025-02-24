from fastapi import FastAPI
from app.routes import router
from app.database import  engine
from app.models import Base
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

Base.metadata.create_all(bind=engine)

app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)

@app.get('/')
def home():

    return {"hello": "world"}
