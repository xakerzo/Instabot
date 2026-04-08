from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, select, update
from datetime import datetime
from config import Config

engine = create_async_engine(Config.DB_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    full_name: Mapped[str] = mapped_column(String, nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    downloads_today: Mapped[int] = mapped_column(Integer, default=0)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MediaCache(Base):
    __tablename__ = "media_cache"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    file_id: Mapped[str] = mapped_column(String)
    media_type: Mapped[str] = mapped_column(String) # 'video', 'audio', 'image'
    file_size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

async def init_db(ctx=None):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_user(user_id: int):
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

async def add_user(user_id: int, full_name: str, username: str):
    async with SessionLocal() as session:
        user = await get_user(user_id)
        if not user:
            user = User(id=user_id, full_name=full_name, username=username)
            session.add(user)
            await session.commit()
        return user

async def get_cached_media(url_hash: str):
    async with SessionLocal() as session:
        result = await session.execute(select(MediaCache).where(MediaCache.url_hash == url_hash))
        return result.scalars().first()

async def add_to_cache(url_hash: str, file_id: str, media_type: str, file_size: int):
    async with SessionLocal() as session:
        cache = MediaCache(url_hash=url_hash, file_id=file_id, media_type=media_type, file_size=file_size)
        session.add(cache)
        await session.commit()
