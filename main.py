import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import db, create_document, get_documents

# =====================
# Auth / Security Setup
# =====================
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12

# Use pbkdf2_sha256 to avoid external bcrypt dependency issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Seed admin credentials via env (for demo)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@portfolio.dev")
# Support providing a precomputed hash; otherwise hash the provided password (short default)
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH") or pwd_context.hash(os.getenv("ADMIN_PASSWORD", "admin123"))

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: str
    password: str

# ============
# Content DTOs
# ============
class TechItem(BaseModel):
    name: str
    category: Optional[str] = "general"
    level: Optional[str] = None
    icon: Optional[str] = None

class Project(BaseModel):
    title: str
    slug: str
    summary: str
    tags: List[str] = []
    tech: List[str] = []
    cover: Optional[str] = None
    logo: Optional[str] = None
    demo_url: Optional[str] = None
    repo_url: Optional[str] = None
    tldr: Optional[str] = None
    role: Optional[str] = None
    timeline: Optional[str] = None
    wireframes: List[str] = []
    screenshots: List[str] = []
    video: Optional[str] = None
    mermaid: Optional[str] = None
    learnings: List[str] = []
    kpis: List[str] = []

class BlogPost(BaseModel):
    title: str
    slug: str
    excerpt: str
    content: str
    tags: List[str] = []
    read_time: int = 4
    cover: Optional[str] = None

class Experience(BaseModel):
    org: str
    role: str
    start: str
    end: str
    summary: str

class Education(BaseModel):
    school: str
    degree: str
    start: str
    end: str
    summary: str

# ==================
# FastAPI app config
# ==================
app = FastAPI(title="Portfolio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========
# Utilities
# =========

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_admin(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email != ADMIN_EMAIL or role != "admin":
            raise HTTPException(status_code=403, detail="Forbidden")
        return {"email": email, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ======
# Routes
# ======
@app.get("/")
def root():
    return {"status": "ok", "service": "portfolio-api"}

@app.get("/test")
def test_database():
    ok = bool(db)
    collections = []
    if ok:
        try:
            collections = db.list_collection_names()
        except Exception:
            pass
    return {"backend": "running", "database": "connected" if ok else "not-available", "collections": collections[:10]}

# Auth
@app.post("/api/auth/login", response_model=Token)
def login(data: LoginRequest):
    if data.email.lower() != ADMIN_EMAIL.lower() or not verify_password(data.password, ADMIN_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": ADMIN_EMAIL, "role": "admin"})
    return Token(access_token=token)

# Projects
@app.get("/api/projects")
def list_projects():
    items = get_documents("project") if db else []
    # normalize _id to string
    for it in items:
        it["id"] = str(it.get("_id"))
        it.pop("_id", None)
    return items

@app.get("/api/projects/{slug}")
def get_project(slug: str):
    items = get_documents("project", {"slug": slug}) if db else []
    if not items:
        raise HTTPException(status_code=404, detail="Not found")
    it = items[0]
    it["id"] = str(it.get("_id"))
    it.pop("_id", None)
    return it

@app.post("/api/projects")
def create_project(project: Project, _: dict = Depends(get_current_admin)):
    _id = create_document("project", project)
    return {"id": _id}

@app.put("/api/projects/{slug}")
def update_project(slug: str, project: Project, _: dict = Depends(get_current_admin)):
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")
    res = db["project"].find_one_and_update({"slug": slug}, {"$set": project.model_dump(), "$currentDate": {"updated_at": True}}, return_document=True)
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}

@app.delete("/api/projects/{slug}")
def delete_project(slug: str, _: dict = Depends(get_current_admin)):
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")
    res = db["project"].delete_one({"slug": slug})
    return {"deleted": res.deleted_count}

# Tech
@app.get("/api/tech")
def list_tech():
    items = get_documents("techitem") if db else []
    for it in items:
        it["id"] = str(it.get("_id"))
        it.pop("_id", None)
    return items

@app.post("/api/tech")
def create_tech(item: TechItem, _: dict = Depends(get_current_admin)):
    _id = create_document("techitem", item)
    return {"id": _id}

# Blog
@app.get("/api/posts")
def list_posts():
    items = get_documents("blogpost") if db else []
    for it in items:
        it["id"] = str(it.get("_id"))
        it.pop("_id", None)
    # latest three
    items.sort(key=lambda x: x.get("created_at", datetime.utcnow()), reverse=True)
    return items[:3]

@app.post("/api/posts")
def create_post(post: BlogPost, _: dict = Depends(get_current_admin)):
    _id = create_document("blogpost", post)
    return {"id": _id}

# Experience & Education (read-only listing endpoints)
@app.get("/api/experience")
def get_experience():
    items = get_documents("experience") if db else []
    for it in items:
        it["id"] = str(it.get("_id"))
        it.pop("_id", None)
    return items

@app.get("/api/education")
def get_education():
    items = get_documents("education") if db else []
    for it in items:
        it["id"] = str(it.get("_id"))
        it.pop("_id", None)
    return items
