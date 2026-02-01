from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import parcels

app = FastAPI(
    title="Clark County Real Estate Intelligence",
    version="1.0.0"
)

# CORS Configuration (Vital for Next.js to talk to Python)
origins = [
    "http://localhost:3000",  # Your local frontend
    "https://your-vercel-app.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the Router
app.include_router(parcels.router, prefix="/api/v1/parcels", tags=["parcels"])

@app.get("/health")
def health_check():
    return {"status": "operational", "service": "clark-bi-backend"}