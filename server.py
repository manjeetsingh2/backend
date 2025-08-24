from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import uuid
import ssl
import jwt
from datetime import datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# ------------------------------
# Environment & runtime settings
# ------------------------------

from dotenv import load_dotenv
load_dotenv()

USE_HTTPS = os.getenv("USE_HTTPS", "false").lower() == "true"
HTTP_PORT = int(os.getenv("HTTP_PORT", 8000))
HTTPS_PORT = int(os.getenv("HTTPS_PORT", 8443))
PORT = HTTPS_PORT if USE_HTTPS else HTTP_PORT
PROTOCOL = "https" if USE_HTTPS else "http"

# ------------------------------
# FastAPI app
# ------------------------------

app = FastAPI(
    title="AGRI - Crop Target Management System",
    description="Agricultural Crop Target Management System for Village Officers and Block Officers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ------------------------------
# CORS
# ------------------------------

def get_cors_origins() -> list[str]:
    if USE_HTTPS:
        raw = os.getenv("CORS_ORIGINS_HTTPS", "https://localhost:3000")
    else:
        raw = os.getenv("CORS_ORIGINS_HTTP", "http://localhost:3000,http://127.0.0.1:3000")
    origins = []
    for o in (x.strip() for x in raw.split(",")):
        if not o:
            continue
        origins.append(o[:-1] if o.endswith("/") else o)
    return origins

ALLOWED_ORIGINS = get_cors_origins()
print(f"[CORS] USE_HTTPS={USE_HTTPS} -> allow_origins={ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# Security / JWT
# ------------------------------

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-dev")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token")
        return sub
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ------------------------------
# Database
# ------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/crop_target_db")
is_sqlite = DATABASE_URL.startswith("sqlite")

engine_kwargs: Dict[str, Any] = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# UUID columns per backend
if is_sqlite:
    from sqlalchemy import String as UUIDType
    def uuid_column():
        return Column(UUIDType(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    def uuid_fk():
        return Column(UUIDType(36), nullable=False, index=True)
    def uuid_fk_opt():
        return Column(UUIDType(36), index=True)
else:
    from sqlalchemy.dialects.postgresql import UUID as UUIDType
    def uuid_column():
        return Column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    def uuid_fk():
        return Column(UUIDType(as_uuid=True), nullable=False, index=True)
    def uuid_fk_opt():
        return Column(UUIDType(as_uuid=True), index=True)

# ------------------------------
# Models
# ------------------------------

class User(Base):
    __tablename__ = "users"
    id = uuid_column()
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(10), nullable=False, index=True)  # VO or BO
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    failed_login_count = Column(Integer, default=0, nullable=False)
    last_failed_login_at = Column(DateTime, nullable=True)
    locked_until = Column(DateTime, nullable=True)

class CropTarget(Base):
    __tablename__ = "crop_targets"
    id = uuid_column()
    year = Column(Integer, nullable=False, index=True)
    season = Column(String(50), nullable=False, index=True)
    village = Column(String(100), nullable=False, index=True)
    crop = Column(String(100), nullable=False, index=True)
    variety = Column(String(100), nullable=False, index=True)
    target_area = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)
    status = Column(String(20), default="draft", nullable=False, index=True)
    rejection_comments = Column(Text)
    submitted_by = uuid_fk()
    submitted_at = Column(DateTime)
    approved_by = uuid_fk_opt()
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ------------------------------
# DB utilities / deps
# ------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------
# Seed default users
# ------------------------------

def init_default_users():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            vo = User(username="vo_user", password_hash=pwd_context.hash("password123"), role="VO")
            bo = User(username="bo_user", password_hash=pwd_context.hash("password123"), role="BO")
            db.add_all([vo, bo])
            db.commit()
            print(f"✅ Default users created (vo_user, bo_user) - {PROTOCOL.upper()}:{PORT}")
    except Exception as e:
        print(f"❌ Error creating default users: {e}")
        db.rollback()
    finally:
        db.close()

init_default_users()

# ------------------------------
# Schemas
# ------------------------------

class UserCreate(BaseModel):
    username: str
    password: str
    role: str  # VO or BO

class UserLogin(BaseModel):
    username: str
    password: str

class CropTargetCreate(BaseModel):
    year: int
    season: str
    village: str
    crop: str
    variety: str
    target_area: float
    date: str

class CropTargetUpdate(BaseModel):
    year: Optional[int] = None
    season: Optional[str] = None
    village: Optional[str] = None
    crop: Optional[str] = None
    variety: Optional[str] = None
    target_area: Optional[float] = None
    date: Optional[str] = None

class ApprovalAction(BaseModel):
    status: str
    rejection_comments: Optional[str] = None

# ------------------------------
# Helpers
# ------------------------------

def get_current_user(user_id: str = Depends(verify_token), db: Session = Depends(get_db)) -> Dict[str, str]:
    if is_sqlite:
        user = db.query(User).filter(User.id == user_id).first()
    else:
        import uuid as u
        user = db.query(User).filter(User.id == u.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": str(user.id), "username": user.username, "role": user.role}

def require_role(allowed: List[str]):
    def _checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return _checker

# ------------------------------
# Routes
# ------------------------------

@app.get("/ping")
async def ping():
    return {"ok": True}

@app.get("/")
async def root():
    return {
        "message": "AGRI - Crop Target Management System",
        "status": "running",
        "database": "SQLite" if is_sqlite else "PostgreSQL",
        "protocol": PROTOCOL.upper(),
        "port": PORT,
        "https_enabled": USE_HTTPS,
    }

@app.get("/health")
async def health():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    return {
        "status": "ok",
        "message": "API is running",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "database": db_status,
        "protocol": PROTOCOL.upper(),
        "port": PORT,
        "https_enabled": USE_HTTPS,
        "cors_origins": ALLOWED_ORIGINS,
    }

# Auth
@app.post("/api/v1/auth/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    u = User(username=user.username, password_hash=pwd_context.hash(user.password), role=user.role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"success": True, "message": "User registered successfully", "data": {"id": str(u.id), "username": u.username, "role": u.role}}

@app.post("/api/v1/auth/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not pwd_context.verify(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": str(db_user.id)})
    return {"success": True, "message": "Login successful", "data": {"access_token": token, "user": {"id": str(db_user.id), "username": db_user.username, "role": db_user.role}}}

# VO endpoints (sample)
@app.post("/api/v1/vo/crop-targets")
async def create_crop_target(payload: CropTargetCreate, current_user: dict = Depends(require_role(["VO"])), db: Session = Depends(get_db)):
    try:
        dt = datetime.strptime(payload.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    ct = CropTarget(
        year=payload.year,
        season=payload.season,
        village=payload.village,
        crop=payload.crop,
        variety=payload.variety,
        target_area=payload.target_area,
        date=dt,
        submitted_by=current_user["id"],
        status="submitted",
        submitted_at=datetime.utcnow(),
    )
    db.add(ct)
    db.commit()
    db.refresh(ct)
    return {"success": True, "message": "Crop target created", "data": {"id": str(ct.id)}}

# ------------------------------
# HTTPS support (local/dev)
# ------------------------------

def create_ssl_context():
    if not USE_HTTPS:
        return None
    cert_path = os.getenv("SSL_CERT_PATH", "./certs/cert.pem")
    key_path = os.getenv("SSL_KEY_PATH", "./certs/key.pem")
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print(f"⚠️ SSL certs not found. To use HTTPS, create\n  SSL_CERT_PATH={cert_path}\n  SSL_KEY_PATH={key_path}")
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
    return ctx

# ------------------------------
# Entrypoint
# ------------------------------

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting AGRI API on {PROTOCOL.upper()}://0.0.0.0:{PORT}")
    print(f"📚 Docs: {PROTOCOL}://localhost:{PORT}/docs")
    ssl_context = create_ssl_context() if USE_HTTPS else None
    uvicorn.run(app, host="0.0.0.0", port=PORT, ssl_certfile=os.getenv("SSL_CERT_PATH") if ssl_context else None, ssl_keyfile=os.getenv("SSL_KEY_PATH") if ssl_context else None)
