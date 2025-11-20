import requests
from sqlalchemy.orm import Session

from src.price.config import price_settings


class PriceService:
    def __init__(self, db: Session):
        self.db = db

    def fetch_all_prices(self) -> list[dict]:
        response = requests.get(
            price_settings.PRICE_API_URL,
            params={
                "CategoryName": price_settings.DEFAULT_CATEGORY,
                "Name": price_settings.DEFAULT_NAME,
            },
            timeout=price_settings.PRICE_FETCH_TIMEOUT,
        )
        return response.json()
