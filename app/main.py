from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.catalog.router import router as catalog_router
from app.core.config import settings
from app.inventory.router import router as inventory_router
from app.routes import health
from app.stores.router import router as stores_router
from app.stores.store_products_router import router as store_products_router

# Access your variables dynamically
app = FastAPI(
    title="Local Basket API",
    debug=(settings.environment == "development")
)

app.include_router(health.router)
app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(inventory_router)
app.include_router(stores_router)
app.include_router(store_products_router)
