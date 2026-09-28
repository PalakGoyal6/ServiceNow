from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.db import engine, Base, SessionLocal
from backend.app.routers import auth, student, staff, admin
from backend.app.services.priority import recompute_all_open_priorities


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is created
    Base.metadata.create_all(bind=engine)
    
    # Run startup priority recomputation across all open issues (§9)
    db = SessionLocal()
    try:
        recompute_all_open_priorities(db)
    except Exception as e:
        print(f"Startup priority recompute warning: {e}")
    finally:
        db.close()
    
    yield


app = FastAPI(
    title="Student Support Triage & Case Management API",
    description="Backend API for cross-department student support triage, priority inheritance, and joined-up case management",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(student.router)
app.include_router(staff.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Student Support Triage & Joined-Up Case Management API",
        "demo_mode": settings.DEMO_MODE,
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
