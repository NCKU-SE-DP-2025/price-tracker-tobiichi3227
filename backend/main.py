import asyncio
import json
import logging
import os
from collections.abc import Generator
from datetime import datetime, timedelta
from enum import IntEnum, auto
from functools import partial
from urllib.parse import quote

import requests
import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from openai import OpenAI
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    create_engine,
    delete,
    insert,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///news_database.db")
        self.jwt_secret = os.getenv("JWT_SECRET", "1892dhianiandowqd0n")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "xxx")
        self.sentry_dsn = os.getenv(
            "SENTRY_DSN",
            "https://4001ffe917ccb261aa0e0c34026dc343@o4505702629834752.ingest.us.sentry.io/4507694792704000",
        )
        self.cors_origins = ["http://localhost:8080"]
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_minutes = 30


settings = Settings()

Base = declarative_base()

user_news_association_table = Table(
    "user_news_upvote_cnt",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column(
        "news_articles_id", Integer, ForeignKey("news_articles.id"), primary_key=True
    ),
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    upvoted_news = relationship(
        "NewsArticle",
        secondary=user_news_association_table,
        back_populates="upvoted_by_users",
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    time = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    upvoted_by_users = relationship(
        "User", secondary=user_news_association_table, back_populates="upvoted_news"
    )


engine = create_engine(settings.database_url, echo=True)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)


# Pydantic schemas
class UserAuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    username: str

    class Config:
        from_attributes = True


class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)


class NewsSummaryRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class NewsSummaryResponse(BaseModel):
    summary: str
    reason: str


class NewsArticleResponse(BaseModel):
    id: int
    title: str
    url: str
    time: str
    content: str
    summary: str
    reason: str
    upvote_cnt: int
    is_upvoted: bool

    class Config:
        from_attributes = True


# service


class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def authenticate_user(self, db: Session, username: str, password: str):
        user = db.query(User).filter(User.username == username).first()
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_token(self, username: str, expire_minutes: int = 30) -> str:
        expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
        payload = {"sub": username, "exp": expire}
        return jwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )

    def verify_token(self, token: str) -> str:
        try:
            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            username = payload.get("sub")
            if not username:
                raise ValueError("Invalid token")
            return username
        except JWTError as exc:
            raise ValueError("Invalid token") from exc


class AIService:
    RELEVANCE_SYSTEM_PROMPT = (
        "你是一個關聯度評估機器人，請評估新聞標題是否與「民生用品的價格變化」相關，"
        "並給予'high'、'medium'、'low'評價。"
        "(僅需回答'high'、'medium'、'low'三個詞之一)"
    )
    SUMMARY_SYSTEM_PROMPT = (
        "你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 "
        "(影響、原因各50個字，請以json格式回答 "
        "{'影響': '...', '原因': '...'})"
    )
    KEYWORD_EXTRACTION_SYSTEM_PROMPT = (
        "你是一個關鍵字提取機器人，用戶將會輸入一段文字，表示其希望看見的新聞內容，"
        "請提取出用戶希望看見的關鍵字，請截取最重要的關鍵字即可，"
        "避免出現「新聞」、「資訊」等混淆搜尋引擎的字詞。"
        "(僅須回答關鍵字，若有多個關鍵字，請以空格分隔)"
    )

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)

    def evaluate_relevance(self, title: str) -> str:
        return self._call_ai(self.RELEVANCE_SYSTEM_PROMPT, title)

    def summarize_news(self, content: str) -> dict:
        result = self._call_ai(self.SUMMARY_SYSTEM_PROMPT, content)
        return json.loads(result)

    def extract_keywords(self, prompt: str) -> str:
        return self._call_ai(self.KEYWORD_EXTRACTION_SYSTEM_PROMPT, prompt)

    def _call_ai(self, system: str, user_content: str) -> str:
        completion = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        )
        return completion.choices[0].message.content


class NewsRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_news_article(self, news_data: dict) -> NewsArticle:
        article = NewsArticle(
            url=news_data["url"],
            title=news_data["title"],
            time=news_data["time"],
            content=news_data["content"],
            summary=news_data["summary"],
            reason=news_data["reason"],
        )
        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)
        return article

    def get_all_articles(self) -> list[NewsArticle]:
        return self.db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()

    def get_article_by_id(self, article_id: int) -> NewsArticle | None:
        return self.db.query(NewsArticle).filter_by(id=article_id).first()

    def count_upvote(self, article_id: int) -> int:
        return (
            self.db.query(user_news_association_table)
            .filter_by(news_articles_id=article_id)
            .count()
        )

    def is_upvoted_by_user(self, article_id: int, user_id: int) -> bool:
        return (
            self.db.query(user_news_association_table)
            .filter_by(news_articles_id=article_id, user_id=user_id)
            .first()
            is not None
        )

    def toggle_upvote(self, article_id: int, user_id: int) -> bool:
        if self.is_upvoted_by_user(article_id, user_id):
            delete_stmt = delete(user_news_association_table).where(
                user_news_association_table.c.news_articles_id == article_id,
                user_news_association_table.c.user_id == user_id,
            )
            self.db.execute(delete_stmt)
            self.db.commit()
            return False

        else:
            insert_stmt = insert(user_news_association_table).values(
                news_articles_id=article_id, user_id=user_id
            )
            self.db.execute(insert_stmt)
            self.db.commit()
            return True


class NewsService:
    UDN_API_URL = "https://udn.com/api/more"

    def __init__(self, db: Session, ai_service: AIService) -> None:
        self.repo = NewsRepository(db)
        self.ai_service = ai_service

    def fetch_and_process_news(
        self, search_term: str, is_initial: bool = False
    ) -> None:
        raw_news = self._fetch_raw_news(search_term, is_initial)
        for news in raw_news:
            try:
                self._process_single_news(news)
            except Exception as e:
                logging.error(f"Error processing news {news.get('titleLink')}: {e}")

    def _process_single_news(self, raw_news: dict):
        relevance = self.ai_service.evaluate_relevance(raw_news["title"])
        if relevance != "high":
            return

        detailed = self._fetch_detailed_news(raw_news["titleLink"])
        if not detailed:
            return

        summary_data = self.ai_service.summarize_news(detailed["content"])
        detailed["summary"] = summary_data["影響"]
        detailed["reason"] = summary_data["原因"]

        self.repo.add_news_article(detailed)

    def _fetch_raw_news(self, search_term: str, is_initial: bool = False) -> list[dict]:
        all_news = []
        pages = range(1, 10) if is_initial else range(1, 2)

        for page in pages:
            params = {
                "page": page,
                "id": f"search:{quote(search_term)}",
                "channelId": 2,
                "type": "searchword",
            }

            try:
                response = requests.get(self.UDN_API_URL, params=params, timeout=10)
                all_news.extend(response.json().get("lists", []))
            except Exception as e:
                logging.error(f"Error fetching raw news for page {page}: {e}")

        return all_news

    def _fetch_detailed_news(self, url: str) -> dict | None:
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.find("h1", class_="article-content__title").text
            time = soup.find("time", class_="article-content__time").text
            content_section = soup.find("section", class_="article-content__editor")

            paragraphs = [
                p.text
                for p in content_section.find_all("p")
                if p.text.strip() != "" and "▪" not in p.text
            ]

            return {
                "url": url,
                "title": title,
                "time": time,
                "content": "".join(paragraphs),  # NOTE: this is ok
            }

        except Exception as e:
            logging.error(f"Error fetching detailed from {url} news: {e}")
            return None

    def search_by_prompt(self, prompt: str) -> list:
        keyword = self.ai_service.extract_keywords(prompt)
        news_list = self._fetch_raw_news(keyword, is_initial=False)

        results = []
        for news in news_list:
            detailed = self._fetch_detailed_news(news["titleLink"])
            if not detailed:
                continue

            results.append(detailed)

        return sorted(results, key=lambda x: x["time"], reverse=True)


class CategoryKey(IntEnum):
    MILK = auto()
    POWDER = auto()
    RICE = auto()
    EGG = auto()
    OIL = auto()
    TISSUE = auto()
    SAUCE = auto()
    BODY_WASH = auto()
    SHAMPOO = auto()
    SOAP = auto()
    DETERGENT = auto()
    INSTANT_NOODLES = auto()
    FLOUR = auto()
    TOOTHPASTE = auto()
    SUGAR = auto()


categories = {
    CategoryKey.MILK: "鮮乳",
    CategoryKey.POWDER: "奶粉",
    CategoryKey.RICE: "米",
    CategoryKey.EGG: "雞蛋",
    CategoryKey.OIL: "食用油",
    CategoryKey.TISSUE: "衛生紙",
    CategoryKey.SAUCE: "醬油",
    CategoryKey.BODY_WASH: "沐浴乳",
    CategoryKey.SHAMPOO: "洗髮精",
    CategoryKey.SOAP: "香皂",
    CategoryKey.DETERGENT: "洗衣粉",
    CategoryKey.INSTANT_NOODLES: "泡麵",
    CategoryKey.FLOUR: "麵粉",
    CategoryKey.TOOTHPASTE: "牙膏",
    CategoryKey.SUGAR: "糖",
}

commodities = {
    CategoryKey.MILK: {
        "統一瑞穗高優質鮮乳",
        "味全林鳳營鮮乳",
        "光泉鮮乳",
        "光泉乳香世家",
        "福樂一番鮮鮮乳",
    },
    CategoryKey.POWDER: {
        "豐力富全家人營養調製奶粉",
        "安怡長青高鈣奶粉",
        "桂格維他命高鈣奶粉",
        "桂格高鐵高鈣奶粉(膠原蛋白配方)",
        # "克寧即溶奶粉",
        "優生A+育嬰配方奶粉",
        "豐力富Nature幼兒成長奶粉（1-3歲）",
        "S-26金愛兒樂奶粉(0-12月)",
        "S-26金幼兒樂奶粉（1-3歲）",
        "亞培心美力3成長奶粉(1-3歲)",
        "亞培心美力1嬰兒奶粉(0-12個月)",
        "味全果汁奶粉(優鈣多配方)",
    },
    CategoryKey.RICE: {
        "中興世界頂級香米",
        "中興外銷日本的米",
        "三好尊爵皇家香米",
        "三好池鮮米",
        "天生好米黃金比例",
        "三好台梗九號米",
        # "中興東部米",
        "三好皇家香米(15℃系列)",
    },
    CategoryKey.EGG: {
        "義進洗選蛋",
        "泰安寶貝紅蛋",
        # "特選白鮮蛋",
        # "冠軍蛋"
    },
    CategoryKey.OIL: {
        # "得意的一天葵花油",
        # "泰山不飽和健康調合油",
        # "泰山OMEGA3芥花不飽和健康調合油",
        "台糖大豆沙拉油",
        # "統一清爽家芥花油",
    },
    CategoryKey.TISSUE: {
        "得意抽取式衛生紙",
        "柔情抽取式衛生紙",
        "春風平版衛生紙",
        "舒潔平版衛生紙",
        "舒潔威象家用紙巾",
        "五月花盒裝面紙",
    },
    CategoryKey.SAUCE: {
        "龜甲萬甘醇醬油",
        "金蘭甘醇醬油",
        "金蘭醬油",
        "萬家香陳年醬油",
        "萬家香香菇素蠔油",
        "統一四季釀造醬油",
    },
    CategoryKey.BODY_WASH: {
        "嬌生PH5.5沐浴乳",
        "澎澎香浴乳(亮澤滋潤型)",
        # "花王沐浴香皂露(滋潤柔滑型)",
        "Biore淨嫩沐浴乳(浪漫保濕型)",
    },
    CategoryKey.SHAMPOO: {
        "Dove去屑護理洗髮乳",
        "海倫仙度絲去屑洗髮乳(海洋活力)",
        "麗仕柔亮絲滑洗髮乳",
        "飛柔洗髮乳(去頭皮屑熱油)",
        "潘婷洗髮乳(絲質順滑)",
    },
    CategoryKey.SOAP: {
        "麗仕香皂",
        "彎彎浴皂",
        "多芬柔嫩潔膚塊",
    },
    CategoryKey.DETERGENT: {
        # "白蘭強效洗衣粉",
        "白蘭強效潔淨洗衣精",
        "白蘭強效潔淨洗衣粉補充包",
        "一匙靈亮彩洗衣精",
        "一匙靈亮彩洗衣粉",
        "加倍潔防螨潔白超濃縮洗衣粉",
    },
    CategoryKey.INSTANT_NOODLES: {
        "維力炸醬麵",
        "統一肉燥麵",
        "味味麵",
        "味味一品原汁珍味牛肉麵",
    },
    CategoryKey.FLOUR: {
        "日正高筋麵粉",
        "義峰高筋麵粉",
    },
    CategoryKey.TOOTHPASTE: {
        "黑人超氟牙膏",
        "高露潔全效牙膏(專業美白)",
        "舒酸定長效抗敏牙膏(牙齦護理)",
        "白人牙膏家庭號",
        "德恩奈超氟牙膏",
        # "白人牙膏",
    },
    CategoryKey.SUGAR: {
        # "台糖細粒特砂",
        "台糖精製細砂",
        "台糖貳號砂糖",
        "台糖精製特砂",
    },
}


class PriceService:
    PRICE_API_URL = "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice"
    TIMEOUT = 45

    def __init__(self, categories: dict, commodities: dict):
        self.categories = categories
        self.commodities = commodities

    async def fetch_all_prices(self) -> list[dict]:
        loop = asyncio.get_running_loop()
        tasks = []

        for category_key, category_name in self.categories.items():
            for commodity_name in self.commodities[category_key]:
                params = {"CategoryName": category_name, "Name": commodity_name}
                func = partial(
                    requests.get,
                    self.PRICE_API_URL,
                    params=params,
                    timeout=self.TIMEOUT,
                )
                tasks.append(
                    (category_name, commodity_name, loop.run_in_executor(None, func))
                )

        results = await asyncio.gather(
            *[task[2] for task in tasks], return_exceptions=True
        )

        prices = []
        for (category_name, commodity_name, _), response in zip(
            tasks, results, strict=False
        ):
            price = self._process_response(category_name, commodity_name, response)
            if price:
                prices.append(price)

        return prices

    def _process_response(self, category: str, commodity: str, response) -> dict | None:
        if isinstance(response, Exception):
            logging.error(
                f"Error fetching price for {category}-{commodity}: {response}"
            )
            return None

        try:
            if response.status_code != 200:
                logging.error(
                    "Non-200 response for {category}-{commodity}:"
                    f" {response.status_code}"
                )
                return None

            data = response.json()
            if isinstance(data, list) and data:
                return data[0]

            return None
        except Exception as e:
            logging.error(f"Error processing response for {category}-{commodity}: {e}")
            return None


auth_service = AuthService()
ai_service = AIService()
price_service = PriceService(categories, commodities)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_news_service(db: Session = Depends(get_db)) -> NewsService:
    return NewsService(db, ai_service)


def get_price_service_dep() -> PriceService:
    return price_service


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    try:
        username = auth_service.verify_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class NewsScheduler:
    def __init__(self):
        self.schedulers = BackgroundScheduler()

    def start(self):
        db = SessionLocal()
        try:
            if db.query(NewsArticle).count() == 0:
                logging.info("Database empty, performing initial news fetch.")
                self._fetch_news(is_initial=True)

            self.schedulers.add_job(
                self._fetch_news,
                "interval",
                minutes=100,
                id="fetch_news",
            )
            self.schedulers.start()
            logging.info("News scheduler started.")
        finally:
            db.close()

    def shutdown(self):
        if self.schedulers.running:
            self.schedulers.shutdown()
            logging.info("News scheduler shut down.")

    def _fetch_news(self, is_initial=False):
        db = SessionLocal()
        try:
            news_service = NewsService(db, ai_service)
            news_service.fetch_and_process_news("價格", is_initial=is_initial)
            logging.info("Scheduled news fetch completed.")
        except Exception as e:
            logging.error(f"Error in scheduled news fetch: {e}")
        finally:
            db.close()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,  # noqa
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

news_scheduler = NewsScheduler()


@app.on_event("startup")
async def startup_event():
    logging.info("Starting up the application...")
    news_scheduler.start()


@app.on_event("shutdown")
def shutdown_event():
    logging.info("Shutting down the application...")
    news_scheduler.shutdown()


auth_router = APIRouter(prefix="/api/v1/users")


@auth_router.post("/register")
def register(user: UserAuthRequest, db: Session = Depends(get_db)):
    is_existing = db.query(User).filter(User.username == user.username).first()
    if is_existing:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = auth_service.hash_password(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserResponse.from_orm(db_user)


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = auth_service.create_token(
        username=user.username, expire_minutes=settings.jwt_expiration_minutes
    )
    return TokenResponse(access_token=access_token)


@auth_router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.from_orm(current_user)


app.include_router(auth_router)


news_router = APIRouter(prefix="/api/v1/news")


@news_router.get("/news", response_model=list[NewsArticleResponse])
def get_news(db: Session = Depends(get_db)):
    repo = NewsRepository(db)
    articles = repo.get_all_articles()

    return [
        NewsArticleResponse(
            **article.__dict__,
            upvote_cnt=repo.count_upvote(article.id),
            is_upvoted=False,
        )
        for article in articles
    ]


@news_router.get("/user_news", response_model=list[NewsArticleResponse])
def get_user_news(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    repo = NewsRepository(db)
    articles = repo.get_all_articles()

    return [
        NewsArticleResponse(
            **article.__dict__,
            upvote_cnt=repo.count_upvote(article.id),
            is_upvoted=repo.is_upvoted_by_user(article.id, current_user.id),
        )
        for article in articles
    ]


@news_router.post("/search_news", response_model=list[dict])
async def search_news(
    prompt_request: PromptRequest,
    news_service: NewsService = Depends(get_news_service),
):
    results = news_service.search_by_prompt(prompt_request.prompt)
    return results


@news_router.post("/news_summary", response_model=NewsSummaryResponse)
async def news_summary(
    payload: NewsSummaryRequest,
    user: User = Depends(get_current_user),
    news_service: NewsService = Depends(get_news_service),
):
    summary = news_service.ai_service.summarize_news(payload.content)
    return NewsSummaryResponse(summary=summary["影響"], reason=summary["原因"])


@news_router.post("/news/{article_id}/upvote")
async def upvote_news(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = NewsRepository(db)
    upvoted = repo.toggle_upvote(article_id, current_user.id)

    if upvoted:
        return {"message": "Article upvoted"}
    else:
        return {"message": "Upvote removed"}


app.include_router(news_router)


price_router = APIRouter(prefix="/api/v1/prices")


@price_router.get("/necessities-price")
async def get_necessities_prices(
    price_service: PriceService = Depends(get_price_service_dep),
):
    prices = await price_service.fetch_all_prices()
    return prices


app.include_router(price_router)
