from fastapi import FastAPI
from app.config import settings
from app.routes import health

# Access your variables dynamically
app = FastAPI(
    title="Local Basket API",
    debug=(settings.ENVIRONMENT == "development")
)

app.include_router(health.router)
