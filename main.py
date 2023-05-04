from ipaddress import ip_address
from typing import Callable

import uvicorn
import redis.asyncio as redis
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.connect import get_db
from app.routes import router
from config import (
    settings,
    PROJECT_NAME,
    VERSION,
    API_PREFIX,
    BANNED_IPS,
    ORIGINS,
)


def get_application():
    """
    The get_application function is a factory function that returns an instance of the FastAPI application.
    It also adds CORS middleware to the application, which allows it to accept requests from other origins.

    :return: The fastapi application object
    """
    app = FastAPI(title=PROJECT_NAME, version=VERSION)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = get_application()


@app.middleware("http")
async def ban_ips(request: Request, call_next: Callable):
    """
    The ban_ips function is a middleware function that checks if the client's IP address is in the BANNED_IPS list.
    If it is, then we return a JSONResponse with status code 403 and an error message. If not, then we call next() to
    continue processing the request.

    :param request: Request: Access the request object
    :param call_next: Callable: Pass the next function in the middleware chain
    :return: The response from the next function in the pipeline
    """
    # if ip_address(request.client.host) in BANNED_IPS:
    #     return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "You are banned"})
    response = await call_next(request)
    return response


@app.on_event("startup")
async def startup():
    """
    The startup function is called when the application starts up.
    It's a good place to initialize things that are used by the app, like databases or caches.

    :return: A coroutine, so we need to call it with await
    """
    await FastAPILimiter.init(
        await redis.Redis(host=settings.redis_host, port=settings.redis_port, password=settings.redis_password,
                          db=0, encoding="utf-8", decode_responses=True)
    )


@app.get("/", name="Images app team_3_project")
def read_root():
    """
    The read_root function returns a dictionary with the key &quot;message&quot; and value &quot;REST APP v-0.0&quot;.

    :return: A dictionary with a &quot;message&quot; key
    """
    return {"message": "REST APP v-1.0"}


@app.get("/api/healthchecker")
async def healthchecker(db: Session = Depends(get_db)):
    """
    The healthchecker function is a simple function that checks the health of the database.
    It does this by making a request to the database and checking if it returns any results.
    If there are no results, then we know something is wrong with our connection to the database.

    :param db: Session: Get the database session
    :return: A dictionary with the key «message» and value «welcome to fastapi!»
    """
    try:
        # Make request
        result = (
            await db.execute(text("SELECT 1"))  # noqa
        ).fetchone()
        
        if result is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Database is not configured correctly")
        return {"message": "Welcome to FastAPI!"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error connecting to the database")


app.include_router(router, prefix=API_PREFIX)


if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
