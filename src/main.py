from fastapi import FastAPI, Request #FAst api creates app and represents an incoming HTTP request (used in error handler)
from fastapi.responses import JSONResponse  # Lets you manually return a JSON response with a custom status code

from src.api.v1 import v1_router


# Creates the FastAPI application. The title, description, version only appear in the auto-generated docs at:
# http://127.0.0.1:8000/docs

app = FastAPI(
    title="Banyan Cloud Employee Management",
    description="Microservice for managing employees, groups, and assignments.",
    version="1.0.0",
)

app.include_router(v1_router) #Register all routes

#If any unhandled error happens anywhere in the app (DB crash, bug in code, etc.), instead of showing a scary Python traceback to the user, it returns: { "detail": "Internal server error" }
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}

#Why it exists:

# DevOps/monitoring tools ping this to check if the server is alive
# Load balancers use it to know if the service is healthy
# You can test it anytime: GET http://127.0.0.1:8000/health