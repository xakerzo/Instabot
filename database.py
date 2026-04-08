import datetime
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Text, Boolean, func
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
    original_url = Column(String(1024))
    file_id = Column(String(512))
    file_type = Column(String(50)) 
    file_size = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Channel(Base):
    __tablename__ = 'channels'
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True)
    title = Column(String(255))
    url = Column(String(255))

class Setting(Base):
    __tablename__ = 'settings'
    key = Column(String(50), primary_key=True)
    value = Column(Text)

class Stat(Base): # Stat klassi borligini ta'minlaymiz
    __tablename__ = 'stats'
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True)
    value = Column(Integer, default=0)

engine = create_async_engine(Config.DB_URL)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db(ctx=None):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Setting).where(Setting.key == 'custom_caption'))
        if not res.scalar():
            session.add(Setting(key='custom_caption', value=""))
        
        # Stat uchun total_downloads ni yaratish
        res_stat = await session.execute(select(Stat).where(Stat.key == 'total_downloads'))
        if not res_stat.scalar():
            session.add(Stat(key='total_downloads', value=0))
            
        await session.commit()

async def add_user(user_id: int, username: str):
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            session.add(User(id=user_id, username=username))
            await session.commit()

async def get_all_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.id))
        return result.scalars().all()

async def get_users_count():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(User.id)))
        return result.scalar()

async def add_to_cache(url_hash: str, file_id: str, file_type: str, file_size: int, original_url: str = None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Cache).where(Cache.url_hash == url_hash))
        if result.scalar(): return
        session.add(Cache(url_hash=url_hash, file_id=file_id, file_type=file_type, file_size=file_size, original_url=original_url))
        await session.commit()

async def get_from_cache(url_hash: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Cache).where(Cache.url_hash == url_hash))
        return result.scalar()

async def increment_stats(): # Funksiya aniq qo'shildi
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stat).where(Stat.key == 'total_downloads'))
        stat = result.scalar()
        if stat:
            stat.value += 1
            await session.commit()

# Kanallar boshqaruvi
async def add_channel(chat_id: int, title: str, url: str):
    async with AsyncSessionLocal() as session:
        session.add(Channel(chat_id=chat_id, title=title, url=url))
        await session.commit()

async def get_channels():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Channel))
        return result.scalars().all()

async def delete_channel(chat_id: int):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Channel).where(Channel.chat_id == chat_id))
        channel = res.scalar()
        if channel:
            await session.delete(channel)
            await session.commit()

# Sozlamalar boshqaruvi
async def set_setting(key: str, value: str):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Setting).where(Setting.key == key))
        setting = res.scalar()
        if setting:
            setting.value = value
        else:
            session.add(Setting(key=key, value=value))
        await session.commit()

async def get_setting(key: str, default: str = ""):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Setting).where(Setting.key == key))
        setting = res.scalar()
        return setting.value if setting else default
