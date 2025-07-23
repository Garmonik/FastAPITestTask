import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, Query
from fastapi.exceptions import RequestValidationError
from sqlalchemy import Column, Integer, Text, String, text

from pydantic import BaseModel, constr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from starlette import status
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from bleach import clean as sanitize_html
import re

from starlette.requests import Request
from starlette.responses import JSONResponse

# Environment variables and constants
DB_PATH = os.getenv("DB_PATH", "reviews.db")
MAX_REVIEW_LENGTH = int(os.getenv("MAX_REVIEW_LENGTH", 1000))
positive_patterns = [r"\bхорош\w*", r"\bлюблю\w*", ]
negative_patterns = [r"\bплох\w*", r"\bненавиж\w*", ]

# Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# DataBase
engine = create_async_engine("sqlite+aiosqlite:///{DB_PATH}".format(DB_PATH=DB_PATH))
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

# Models
class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    sentiment = Column(String(10), nullable=False)
    created_at = Column(String(20), nullable=False)

class ReviewPOSTRequest(BaseModel):
    text: constr(strip_whitespace=True, min_length=1, max_length=MAX_REVIEW_LENGTH)

class ReviewResponse(BaseModel):
    id: int
    text: str
    sentiment: str
    created_at: str

async def get_db() -> AsyncSession:
    """A function that opens a connection to a database for subsequent work with it."""
    async with async_session() as session:
        yield session

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info(f"DataBase initialized")
    yield

# Application
app = FastAPI(
    title="Review Sentiment Service",
    description="Service for receiving reviews and conducting segment analysis",
    version="1.0.1",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Third Party Features
def check_sentiment(text: str) -> str:
    """Function to check a string for trigger words"""
    lower_text = text.lower()

    for pattern in positive_patterns:
        if re.search(pattern, lower_text):
            return "positive"

    for pattern in negative_patterns:
        if re.search(pattern, lower_text):
            return "negative"

    return "neutral"

#Errors
@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error("SQLAlchemy Error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal database error"})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request body"}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP error {exc.status_code} on {request.method} {request.url.path}: {exc.detail}")
    detail = "Something went wrong"

    if exc.status_code == 404:
        detail = "Not found"

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail}
    )

# Endpoints
@app.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
        request: ReviewPOSTRequest,
        db: AsyncSession = Depends(get_db)
):
    """Function for creating and checking a review"""
    clear_text = sanitize_html(request.text, tags=[], attributes=[], strip=True)
    sentiment = check_sentiment(clear_text)
    created_at = datetime.now(timezone.utc).isoformat()

    insert_review_sql = text("""
        INSERT INTO reviews (text, sentiment, created_at)
        VALUES (:text, :sentiment, :created_at)
        """)
    await db.execute(insert_review_sql, {
        "text": clear_text,
        "sentiment": sentiment,
        "created_at": created_at
    })
    await db.commit()
    last_id_result = await db.execute(text("SELECT last_insert_rowid()"))
    last_id = last_id_result.scalar()

    return ReviewResponse(
        id=last_id,
        text=clear_text,
        sentiment=sentiment,
        created_at=created_at)

@app.get("/reviews", response_model=list[ReviewResponse])
async def list_reviews(
        sentiment: str | None = Query(
            None,
            pattern="^(positive|negative|neutral)$", description="Filter by sentiment"),
        db: AsyncSession = Depends(get_db)
):
    """Function to get a list of reviews"""
    if sentiment:
        reviews_sql = text("""
        SELECT id, text, sentiment, created_at 
        FROM reviews 
        WHERE sentiment = :sentiment
        """)
        result = await db.execute(reviews_sql, {"sentiment": sentiment})
    else:
        reviews_sql = text("""
                SELECT id, text, sentiment, created_at 
                FROM reviews 
                """)
        result = await db.execute(reviews_sql)

    reviews = result.fetchall()
    return [ReviewResponse(
        id=review.id,
        text=review.text,
        sentiment=review.sentiment,
        created_at=review.created_at
    )
        for review in reviews]

# Running the application locally
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info", reload=True)