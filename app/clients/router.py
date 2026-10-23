from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clients.schemas import ClientProfileCreate, ClientProfileUpdate
from app.clients.service import (
    create_client_profile,
    get_client_profile,
    update_client_profile,
)
from app.contracts import ClientProfile
from app.db.session import get_db

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post(
    "",
    response_model=ClientProfile,
    status_code=status.HTTP_201_CREATED,
)
def create_client(
    data: ClientProfileCreate,
    db: Session = Depends(get_db),
) -> ClientProfile:
    """Создаёт профиль клиента."""
    if get_client_profile(data.client_id, db) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Профиль клиента '{data.client_id}' уже существует",
        )

    try:
        return create_client_profile(data, db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Профиль клиента '{data.client_id}' уже существует",
        )


@router.get("/{client_id}", response_model=ClientProfile)
def read_client(
    client_id: str,
    db: Session = Depends(get_db),
) -> ClientProfile:
    """Возвращает профиль клиента."""
    client = get_client_profile(client_id, db)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Профиль клиента '{client_id}' не найден",
        )
    return client


@router.put("/{client_id}", response_model=ClientProfile)
def update_client(
    client_id: str,
    data: ClientProfileUpdate,
    db: Session = Depends(get_db),
) -> ClientProfile:
    """Полностью обновляет существующий профиль клиента."""
    if data.client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="client_id в URL должен совпадать с client_id в теле",
        )

    client = update_client_profile(client_id, data, db)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Профиль клиента '{client_id}' не найден",
        )
    return client
