from fastapi import FastAPI

app = FastAPI(title="Email Shooter API")

@app.get("/")
async def root():
    return {"message" : "Backend Running"}