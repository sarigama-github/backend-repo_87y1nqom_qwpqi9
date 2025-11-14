"""
Database Schemas for Portfolio CMS

Each Pydantic model = one MongoDB collection (lowercased class name).
"""

from pydantic import BaseModel, Field
from typing import List, Optional

# Auth
class Admin(BaseModel):
    email: str
    password_hash: str
    role: str = Field(default="admin")

# Content
class TechItem(BaseModel):
    name: str
    category: str = Field(default="general")
    level: Optional[str] = None
    icon: Optional[str] = None  # lucide icon name

class Project(BaseModel):
    title: str
    slug: str
    summary: str
    tags: List[str] = []
    tech: List[str] = []
    cover: Optional[str] = None  # image url
    logo: Optional[str] = None
    demo_url: Optional[str] = None
    repo_url: Optional[str] = None
    # detail fields
    tldr: Optional[str] = None
    role: Optional[str] = None
    timeline: Optional[str] = None
    wireframes: List[str] = []  # image urls
    screenshots: List[str] = [] # image urls
    video: Optional[str] = None # mp4 or youtube url
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
