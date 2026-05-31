"""Rotas FastAPI."""
from fastapi import APIRouter, Depends, HTTPException

from src.application.analyze_device import AnalyzeDeviceUseCase
from src.interfaces.api.dependencies import (
    get_analyze_use_case,
    get_api_client,
    get_mongo,
    get_rag_agent,
)
from src.infrastructure.external_api.eletrofrio_client import EletrofrioClient
from src.infrastructure.database.mongo import MongoRepository
from src.agents.rag_agent import RagAgent

router = APIRouter()


@router.get("/health")
async def health(mongo: MongoRepository = Depends(get_mongo)):
    return {"status": "ok", "mongo": await mongo.ping()}


@router.get("/devices/summary")
async def devices_summary(
    api: EletrofrioClient = Depends(get_api_client),
    mongo: MongoRepository = Depends(get_mongo),
):
    """Lista devices únicos (vindos dos alarmes) + última severidade conhecida.

    Usado pela UI para popular a tela inicial do mockup mobile.
    """
    alarms = await api.fetch_alarms()

    # Devices únicos extraídos dos alarmes + metadados de loja
    devices: dict[int, dict] = {}
    for a in alarms:
        dev = a.get("dispositivoId") or a.get("dispositivo_id")
        if not dev:
            continue
        if dev not in devices:
            devices[dev] = {
                "device_id": dev,
                "loja_id": a.get("lojaId") or a.get("loja_id"),
                "loja_nome": a.get("lojaNm") or a.get("lojaNome") or a.get("loja_nome"),
                "tag": a.get("dispositivoNm") or a.get("tag"),
                "alarm_count": 0,
            }
        devices[dev]["alarm_count"] += 1

    # Enriquece com a última severity registrada em agent_decisions
    seen: set[int] = set()
    for doc in await mongo.recent_decisions(500):
        dev = doc.get("device_id")
        if dev in devices and dev not in seen:
            devices[dev]["last_severity"] = doc.get("severity")
            devices[dev]["last_action"] = doc.get("action")
            seen.add(dev)

    return list(devices.values())


@router.get("/analyze/{device_id}")
async def analyze_device(
    device_id: int,
    use_case: AnalyzeDeviceUseCase = Depends(get_analyze_use_case),
):
    try:
        return await use_case.execute(device_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alarms")
async def list_alarms(api: EletrofrioClient = Depends(get_api_client)):
    return await api.fetch_alarms()


@router.get("/units")
async def list_units(api: EletrofrioClient = Depends(get_api_client)):
    return await api.fetch_units()


@router.get("/telemetry/{device_id}")
async def telemetry(device_id: int, api: EletrofrioClient = Depends(get_api_client)):
    return await api.fetch_telemetry(device_id)


@router.get("/notifications")
async def list_notifications(
    limit: int = 50, mongo: MongoRepository = Depends(get_mongo)
):
    """Feed das notificações WhatsApp recentes (debug / UI)."""
    return await mongo.recent_notifications(limit)


@router.post("/rag/query")
async def rag_query(payload: dict, rag: RagAgent = Depends(get_rag_agent)):
    q = payload.get("query", "")
    if not q:
        raise HTTPException(status_code=400, detail="query é obrigatório")
    return {"answer": await rag.diagnose(q)}
