from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.auto_test import TestEnvironment
from app.schemas.auto_test import (
    EnvironmentCreate,
    EnvironmentResponse,
    EnvironmentUpdate,
)

router = APIRouter(tags=["auto-test"])


@router.get("/environments", response_model=list[EnvironmentResponse])
def list_environments(
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db_session),
):
    query = db.query(TestEnvironment)
    if is_active is not None:
        query = query.filter(TestEnvironment.is_active == is_active)
    envs = query.order_by(TestEnvironment.name).all()
    return [EnvironmentResponse.model_validate(e) for e in envs]


@router.post("/environments", response_model=EnvironmentResponse)
def create_environment(
    data: EnvironmentCreate,
    db: Session = Depends(get_db_session),
):
    env = TestEnvironment(
        name=data.name,
        base_url=data.base_url,
        description=data.description,
        variables=json.dumps(data.variables) if data.variables else None,
        is_active=data.is_active,
    )
    db.add(env)
    db.commit()
    db.refresh(env)
    return EnvironmentResponse.model_validate(env)


@router.get("/environments/{env_id}", response_model=EnvironmentResponse)
def get_environment(env_id: str, db: Session = Depends(get_db_session)):
    env = db.query(TestEnvironment).filter(TestEnvironment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    return EnvironmentResponse.model_validate(env)


@router.put("/environments/{env_id}", response_model=EnvironmentResponse)
def update_environment(
    env_id: str,
    data: EnvironmentUpdate,
    db: Session = Depends(get_db_session),
):
    env = db.query(TestEnvironment).filter(TestEnvironment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "variables":
            setattr(env, key, json.dumps(value) if value else None)
        else:
            setattr(env, key, value)

    db.commit()
    db.refresh(env)
    return EnvironmentResponse.model_validate(env)


@router.delete("/environments/{env_id}")
def delete_environment(env_id: str, db: Session = Depends(get_db_session)):
    env = db.query(TestEnvironment).filter(TestEnvironment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    db.delete(env)
    db.commit()
    return {"message": "环境已删除"}
