import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.future import select
from config import Config

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)

class Cache(Base):
    __tablename__ = 'cache'
    id = Column(Integer, primary_key=True)
    url_hash = Column(String(255), unique=True, index=True)
    file_id = Column(String(512))
    file_type = Column(String(50)) # video, audio, photo
    file_size = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Stat(Base):
    __tablename__ = 'stats'
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True)
    value = Column(Integer, default=0)

engine = create_async_engine(Config.DB_URL)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Statistika uchun boshlang'ich qiymat
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stat).where(Stat.key == 'total_downloads'))
        if not result.scalar():
            session.add(Stat(key='total_downloads', value=0))
            await session.commit()

async def add_user(user_id: int, username: str):
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            session.add(User(id=user_id, username=username))
            await session.commit()

async def add_to_cache(url_hash: str, file_id: str, file_type: str, file_size: int):
    async with AsyncSessionLocal() as session:
        cache = Cache(url_hash=url_hash, file_id=file_id, file_type=file_type, file_size=file_size)
        session.add(cache)
        await session.commit()

async def get_from_cache(url_hash: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Cache).where(Cache.url_hash == url_hash))
        return result.scalar()

async def increment_stats():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stat).where(Stat.key == 'total_downloads'))
        stat = result.scalar()
        if stat:
            stat.value += 1
            await session.commit()
