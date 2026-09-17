from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import students, labs, submissions

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LabChecker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students.router)
app.include_router(labs.router)
app.include_router(submissions.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
