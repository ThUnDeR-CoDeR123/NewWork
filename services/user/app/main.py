from fastapi import FastAPI
from app.routes.utils import router
from app.routes.forgetPasswordRoutes import forgetRouter
from app.routes.authRoutes import tokenRouter
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
app.include_router(forgetRouter)
app.include_router(tokenRouter)

@app.get('/')
def home():
    return {"hello": "world"}



