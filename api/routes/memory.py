from fastapi import APIRouter
from api.schemas import MemoryStats
from core.memory import get_memory

router = APIRouter(prefix='/api/memory', tags=['memory'])

@router.get('/stats', response_model=MemoryStats)
async def memory_stats():
    mem = await get_memory()
    return MemoryStats(**(await mem.stats()))

@router.get('/{user_id}')
async def get_user_history(user_id: str, limit: int = 50):
    mem = await get_memory()
    history = await mem.get_history(user_id, limit=limit)
    return {'user_id': user_id, 'count': len(history), 'messages': history}

@router.delete('/{user_id}')
async def clear_user_history(user_id: str):
    mem = await get_memory()
    count = await mem.clear_user(user_id)
    return {'user_id': user_id, 'deleted': count}