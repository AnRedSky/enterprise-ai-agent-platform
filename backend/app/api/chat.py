from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio, json, uuid
from app.core.auth import current_claims

router = APIRouter()
class ChatRequest(BaseModel): input: str; session_id: uuid.UUID | None = None

@router.post("/stream")
async def stream(p: ChatRequest, claims=Depends(current_claims)):
    request_id, trace_id = uuid.uuid4(), uuid.uuid4()
    async def events():
        for item in [{"type":"start","request_id":str(request_id),"trace_id":str(trace_id)}, {"type":"delta","content":f"收到：{p.input}"}, {"type":"done"}]:
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.01)
    return StreamingResponse(events(), media_type="text/event-stream", headers={"X-Request-ID":str(request_id),"X-Trace-ID":str(trace_id)})
