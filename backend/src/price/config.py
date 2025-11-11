from pydantic_settings import BaseSettings


class PriceConfig(BaseSettings):
    PRICE_API_URL: str = (
        "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice"
    )
    PRICE_FETCH_TIMEOUT: int = 45
    PRICE_FETCH_INTERVAL_MINUTES: int = 60

    DEFAULT_CATEGORY: str = "'*'"
    DEFAULT_NAME: str = "'*'"


price_settings = PriceConfig()
