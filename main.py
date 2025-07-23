import os
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, Query
import sqlite3

from pydantic import BaseModel, constr
from starlette import status
from starlette.middleware.cors import CORSMiddleware

from bleach import clean as sanitize_html
import re

DB_PATH = os.getenv("DB_PATH", "reviews.db")
MAX_REVIEW_LENGTH = int(os.getenv("MAX_REVIEW_LENGTH", 1000))
positive_patterns = [r"\bхорош\w*", r"\bлюблю\w*", ]
negative_patterns = [r"\bплох\w*", r"\bненавиж\w*", ]

app = FastAPI(title="Review Sentiment Service",
              discription="Service for receiving reviews and conducting segment analysis",
              version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def init_db():
    """Function to initialize a table in a database (works only with sqlite3)"""
    if not DB_PATH and DB_PATH.endswith(".db"):
        logger.error("DB_PATH must point to a sqlite3 database")
        raise ValueError('DB_URL must be set with .db extension')
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        ''')
        conn.commit()
        conn.close()
        logger.info(f"Database initialized successfully")
    except sqlite3.OperationalError as e:
        logger.error(e)
        raise RuntimeError(f"Failed to connect to database {DB_PATH}: {e}")
    except AttributeError as e:
        logger.error(e)
        raise RuntimeError(f"Failed to connect to database {DB_PATH}: {e}")

def get_db():
    """A function that opens a connection to a database for subsequent work with it."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()


class ReviewPOSTRequest(BaseModel):
    text: constr(strip_whitespace=True, min_length=1, max_length=MAX_REVIEW_LENGTH)


class ReviewResponse(BaseModel):
    id: int
    text: str
    sentiment: str
    created_at: str

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


@app.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
        request: ReviewPOSTRequest,
        db: sqlite3.Connection = Depends(get_db)
):
    """Function for creating and checking a review"""
    clear_text = sanitize_html(request.text, tags=[], attributes=[], strip=True)
    sentiment = check_sentiment(request.text)
    created_at = datetime.now(timezone.utc).isoformat()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO reviews (text, sentiment, created_at) VALUES (?, ?, ?)",
        (clear_text, sentiment, created_at))
    db.commit()
    review_id = cursor.lastrowid
    return ReviewResponse(
        id=review_id,
        text=clear_text,
        sentiment=sentiment,
        created_at=created_at)

@app.get("/reviews", response_model=list[ReviewResponse])
async def list_reviews(
        sentiment: str | None = Query(
            None,
            pattern="^(positive|negative|neutral)$", description="Filter by sentiment"),
        db: sqlite3.Connection = Depends(get_db)
):
    """Function to get a list of reviews"""
    cursor = db.cursor()
    if sentiment:
        cursor.execute(
            "SELECT id, text, sentiment, created_at FROM reviews WHERE sentiment=?",
            (sentiment,)
        )
    else:
        cursor.execute("SELECT id, text, sentiment, created_at FROM reviews")
    rows = cursor.fetchall()
    return [ReviewResponse(id=r[0], text=r[1], sentiment=r[2], created_at=r[3]) for r in rows]

if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info", reload=True)