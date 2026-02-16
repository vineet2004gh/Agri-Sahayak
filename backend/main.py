from fastapi import FastAPI
from backend.routes import router as api_router  
from backend.voice import router as voice_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Setting  up CORS middleware for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router)
app.include_router(voice_router)
