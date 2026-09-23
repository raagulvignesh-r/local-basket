from fastapi import APIRouter

# Initialize the router for this specific domain/feature
router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}
