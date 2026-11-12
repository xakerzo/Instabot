import datetime
import os
import re
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Text, Boolean, func, select, delete, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import Config

# Agar SQLite ishlatilayotgan bo'lsa, baza papkasi mavjudligini ta'minlash
if "sqlite" in Config.DB_URL:
    match = re.search(r"sqlite(?:\+\w+)?:///(.+)", Config.DB_URL)
    if match:
        db_file = match.group(1)
        db_dir = os.path.dirname(db_file)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)

class Cache(Base):
    __tablename__ = 'cache'
    id = Column(Integer, primary_key=True)
    url_hash = Column(String(255), unique=True, index=True)
    original_url = Column(String(1024), nullable=True)
    file_id = Column(String(512))
    file_type = Column(String(50)) # 'video', 'photo', 'album', 'audio'
    file_size = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Channel(Base):
    __tablename__ = 'channels'
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, index=True)
    title = Column(String(255))
    url = Column(String(512))

class Setting(Base):
    __tablename__ = 'settings'
    key = Column(String(50), primary_key=True)
    value = Column(Text, default="")

class Stat(Base):
    __tablename__ = 'stats'
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True)
    value = Column(Integer, default=0)

engine = create_async_engine(Config.DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db(ctx=None):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        # Default settings
        res = await session.execute(select(Setting).where(Setting.key == 'custom_caption'))
        if not res.scalar():
            session.add(Setting(key='custom_caption', value=""))
        
        # Default stats
        res_stat = await session.execute(select(Stat).where(Stat.key == 'total_downloads'))
        if not res_stat.scalar():
            session.add(Stat(key='total_downloads', value=0))
            
        # Agar mavjud foydalanuvchilarda is_active NULL bo'lsa, TRUE ga yangilash
        try:
            await session.execute(text("UPDATE users SET is_active = TRUE WHERE is_active IS NULL"))
        except Exception:
            pass

        await session.commit()

async def add_user(user_id: int, username: Optional[str]):
    if not user_id or user_id <= 0:
        return
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            session.add(User(id=user_id, username=username, is_active=True))
            await session.commit()
        elif not user.is_active or user.username != username:
            user.is_active = True
            user.username = username
            await session.commit()

async def set_user_active(user_id: int, is_active: bool):
    if not user_id or user_id <= 0:
        return
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if user and user.is_active != is_active:
            user.is_active = is_active
            await session.commit()

async def get_all_users(only_active: bool = False) -> List[int]:
    async with AsyncSessionLocal() as session:
        stmt = select(User.id).where(User.id > 0)
        if only_active:
            stmt = stmt.where((User.is_active.is_(True)) | (User.is_active.is_(None)))
        result = await session.execute(stmt)
        return list(result.scalars().all())

async def get_users_count() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(User.id)))
        return result.scalar() or 0

async def get_stats_summary() -> Dict[str, int]:
    async with AsyncSessionLocal() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        active_users = (await session.execute(select(func.count(User.id)).where(User.is_active.is_(True)))).scalar() or 0
        
        stat_res = (await session.execute(select(Stat.value).where(Stat.key == 'total_downloads'))).scalar()
        total_downloads = stat_res if stat_res is not None else 0
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_downloads": total_downloads
        }

async def add_to_cache(url_hash: str, file_id: str, file_type: str, file_size: int, original_url: Optional[str] = None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Cache).where(Cache.url_hash == url_hash))
        cached = result.scalar()
        if cached:
            cached.file_id = file_id
            cached.file_type = file_type
            cached.file_size = file_size
        else:
            session.add(Cache(
                url_hash=url_hash,
                file_id=file_id,
                file_type=file_type,
                file_size=file_size,
                original_url=original_url
            ))
        await session.commit()

async def get_from_cache(url_hash: str) -> Optional[Cache]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Cache).where(Cache.url_hash == url_hash))
        return result.scalar()

async def remove_from_cache(url_hash: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Cache).where(Cache.url_hash == url_hash))
        item = result.scalar()
        if item:
            await session.delete(item)
            await session.commit()

async def increment_stats(key: str = 'total_downloads'):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stat).where(Stat.key == key))
        stat = result.scalar()
        if stat:
            stat.value += 1
        else:
            session.add(Stat(key=key, value=1))
        await session.commit()

async def add_or_update_channel(chat_id: int, title: str, url: str):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Channel).where(Channel.chat_id == chat_id))
        channel = res.scalar()
        if channel:
            channel.title = title
            channel.url = url
        else:
            session.add(Channel(chat_id=chat_id, title=title, url=url))
        await session.commit()

async def get_channels() -> List[Channel]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Channel))
        return list(result.scalars().all())

async def delete_channel(chat_id: int):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Channel).where(Channel.chat_id == chat_id))
        channel = res.scalar()
        if channel:
            await session.delete(channel)
            await session.commit()

async def set_setting(key: str, value: str):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Setting).where(Setting.key == key))
        setting = res.scalar()
        if setting:
            setting.value = value
        else:
            session.add(Setting(key=key, value=value))
        await session.commit()

async def get_setting(key: str, default: str = "") -> str:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Setting).where(Setting.key == key))
        setting = res.scalar()
        return setting.value if setting and setting.value is not None else default

async def clear_all_cache() -> int:
    """
    Bazada saqlangan barcha kesh qatorlarini tozalaydi.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(Cache.id)))
        cnt = result.scalar() or 0
        await session.execute(delete(Cache))
        await session.commit()
        return cnt

async def get_admin_ids() -> List[int]:
    """
    Konfiguratsiyadagi (ENV) va bazadagi barcha admin ID larini yig'ib qaytaradi.
    """
    admins = set(Config.ADMIN_IDS)
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Setting).where(Setting.key == 'admin_ids'))
            setting = res.scalar()
            if setting and setting.value:
                for part in re.findall(r'\d+', setting.value):
                    admins.add(int(part))
    except Exception as e:
        logging.warning(f"Bazadan adminlarni o'qishda xatolik: {e}")
    return list(admins)

async def is_admin(user_id: int) -> bool:
    """
    Foydalanuvchi bot admini ekanligini tekshiradi.
    Agar ENV yoki bazada umuman admin belgilanmagan bo'lsa,
    birinchi murojaat qilgan foydalanuvchini avtomatik admin qiladi.
    """
    if not user_id or user_id <= 0:
        return False
    admins = await get_admin_ids()
    if not admins:
        # Birinchi foydalanuvchini avtomatik admin qilish
        await add_admin(user_id)
        logging.info(f"Botga birinchi admin avtomatik tayinlandi: {user_id}")
        return True
    return user_id in admins

async def add_admin(user_id: int):
    """
    Bazaga yangi admin ID sini qo'shadi.
    """
    if not user_id or user_id <= 0:
        return
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Setting).where(Setting.key == 'admin_ids'))
        setting = res.scalar()
        existing = set(Config.ADMIN_IDS)
        if setting and setting.value:
            existing.update(int(x) for x in re.findall(r'\d+', setting.value))
        existing.add(user_id)
        val = ",".join(str(x) for x in sorted(existing))
        if setting:
            setting.value = val
        else:
            session.add(Setting(key='admin_ids', value=val))
        await session.commit()

async def remove_admin(user_id: int):
    """
    Bazadan admin ID sini o'chiradi (ENV dagilar saqlanib qoladi).
    """
    if not user_id:
        return
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Setting).where(Setting.key == 'admin_ids'))
        setting = res.scalar()
        if setting and setting.value:
            existing = {int(x) for x in re.findall(r'\d+', setting.value)}
            existing.discard(user_id)
            setting.value = ",".join(str(x) for x in sorted(existing))
            await session.commit()
