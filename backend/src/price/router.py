from fastapi import APIRouter, Depends

from src.price.dependencies import get_price_service

router = APIRouter()


@router.get("/necessities-price", response_model=list[dict])
def get_necessities_prices(price_service=Depends(get_price_service)):
    prices = price_service.fetch_all_prices()
    return prices
