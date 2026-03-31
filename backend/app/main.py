from app.db.session import Base, engine
from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="haoxhealth-ai")
app.include_router(router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
