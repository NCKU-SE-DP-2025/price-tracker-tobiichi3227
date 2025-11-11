from fastapi import Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.price.service import PriceService


def get_price_service(db: Session = Depends(get_db)) -> PriceService:
    return PriceService(db)
