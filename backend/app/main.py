from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="WebGuard API",
    description="Automated Web Security Assessment & Misconfiguration Scanner",
    version="0.1.0",
)

# CORS middleware for local frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "WebGuard Security Assessment Engine API is running"}


@app.get("/api/v1/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "webguard-backend"}
