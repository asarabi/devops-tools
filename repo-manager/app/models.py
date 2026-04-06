from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timezone

DATABASE_URL = "sqlite:///data/repo_manager.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    source_type = Column(String, nullable=False)  # gerrit or github
    url = Column(String, nullable=False)
    last_synced = Column(DateTime)
    repositories = relationship("Repository", back_populates="source", cascade="all, delete-orphan")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    state = Column(String, default="ACTIVE")  # ACTIVE, READ_ONLY, HIDDEN
    parent_project = Column(String, default="")  # Gerrit inheritance
    web_url = Column(String, default="")
    default_branch = Column(String, default="")
    updated_at = Column(DateTime)

    source = relationship("Source", back_populates="repositories")
    branches = relationship("Branch", back_populates="repository", cascade="all, delete-orphan")
    permissions = relationship("Permission", back_populates="repository", cascade="all, delete-orphan")


class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    name = Column(String, nullable=False)
    revision = Column(String, default="")

    repository = relationship("Repository", back_populates="branches")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    ref_pattern = Column(String, nullable=False)  # e.g., refs/heads/*
    permission_name = Column(String, nullable=False)  # e.g., push, read
    group_name = Column(String, nullable=False)
    action = Column(String, default="ALLOW")  # ALLOW, DENY, BLOCK

    repository = relationship("Repository", back_populates="permissions")


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
