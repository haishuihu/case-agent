from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.llm_config import (
    EmbeddingConfigCreate,
    EmbeddingConfigResponse,
    EmbeddingConfigUpdate,
    LLMConfigCreate,
    LLMConfigResponse,
    LLMConfigUpdate,
    MigrateStatusResponse,
    SetDefaultResponse,
    TestConnectionRequest,
    TestConnectionResponse,
)
from app.services import llm_config_service as svc

logger = logging.getLogger(__name__)

# ---- LLM Config Router ----

llm_router = APIRouter(prefix="/config/llm", tags=["llm-config"])
embedding_router = APIRouter(prefix="/config/embedding", tags=["embedding-config"])
config_router = APIRouter(prefix="/config", tags=["config"])


# LLM Config endpoints

@llm_router.get("", response_model=list[LLMConfigResponse])
def list_llm_configs(db: Session = Depends(get_db_session)) -> list[LLMConfigResponse]:
    return svc.list_llm_configs(db)


@llm_router.post("", response_model=LLMConfigResponse, status_code=status.HTTP_201_CREATED)
def create_llm_config(
    payload: LLMConfigCreate,
    db: Session = Depends(get_db_session),
) -> LLMConfigResponse:
    return svc.create_llm_config(db, payload)


@llm_router.get("/{config_id}", response_model=LLMConfigResponse)
def get_llm_config(
    config_id: str,
    db: Session = Depends(get_db_session),
) -> LLMConfigResponse:
    config = svc.get_llm_config(db, config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
    return LLMConfigResponse.from_orm(config)


@llm_router.put("/{config_id}", response_model=LLMConfigResponse)
def update_llm_config(
    config_id: str,
    payload: LLMConfigUpdate,
    db: Session = Depends(get_db_session),
) -> LLMConfigResponse:
    result = svc.update_llm_config(db, config_id, payload)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
    return result


@llm_router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_llm_config(
    config_id: str,
    db: Session = Depends(get_db_session),
) -> None:
    ok = svc.delete_llm_config(db, config_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")


@llm_router.post("/{config_id}/set-default", response_model=SetDefaultResponse)
def set_default_llm_config(
    config_id: str,
    db: Session = Depends(get_db_session),
) -> SetDefaultResponse:
    result = svc.set_default_llm_config(db, config_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
    return SetDefaultResponse(ok=True, message=f"已将「{result.name}」设为默认模型")


# Embedding Config endpoints

@embedding_router.get("", response_model=list[EmbeddingConfigResponse])
def list_embedding_configs(db: Session = Depends(get_db_session)) -> list[EmbeddingConfigResponse]:
    return svc.list_embedding_configs(db)


@embedding_router.post("", response_model=EmbeddingConfigResponse, status_code=status.HTTP_201_CREATED)
def create_embedding_config(
    payload: EmbeddingConfigCreate,
    db: Session = Depends(get_db_session),
) -> EmbeddingConfigResponse:
    return svc.create_embedding_config(db, payload)


@embedding_router.get("/{config_id}", response_model=EmbeddingConfigResponse)
def get_embedding_config(
    config_id: str,
    db: Session = Depends(get_db_session),
) -> EmbeddingConfigResponse:
    config = svc.get_embedding_config(db, config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
    return EmbeddingConfigResponse.from_orm(config)


@embedding_router.put("/{config_id}", response_model=EmbeddingConfigResponse)
def update_embedding_config(
    config_id: str,
    payload: EmbeddingConfigUpdate,
    db: Session = Depends(get_db_session),
) -> EmbeddingConfigResponse:
    result = svc.update_embedding_config(db, config_id, payload)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
    return result


@embedding_router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_embedding_config(
    config_id: str,
    db: Session = Depends(get_db_session),
) -> None:
    ok = svc.delete_embedding_config(db, config_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")


# Shared endpoints

@config_router.post("/llm/test-connection", response_model=TestConnectionResponse)
def test_llm_connection(payload: TestConnectionRequest) -> TestConnectionResponse:
    return svc.test_connection(payload)


@config_router.get("/migrate-status", response_model=MigrateStatusResponse)
def get_migrate_status(db: Session = Depends(get_db_session)) -> MigrateStatusResponse:
    needs_llm, needs_emb, env_has_llm, env_has_embedding = svc.needs_migration(db)
    return MigrateStatusResponse(
        needs_migration=needs_llm or needs_emb,
        llm_configs_count=db.query(svc.LLMConfig).count(),
        embedding_configs_count=db.query(svc.EmbeddingConfig).count(),
        env_has_llm_config=env_has_llm,
        env_has_embedding_config=env_has_embedding,
    )


@config_router.post("/migrate", response_model=dict)
def migrate_configs(db: Session = Depends(get_db_session)) -> dict:
    result = svc.migrate_from_env(db)
    return {"ok": True, "migrated": result}
