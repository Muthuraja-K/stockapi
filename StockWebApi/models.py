from pydantic import BaseModel
from typing import Optional, List

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenRequest(BaseModel):
    token: str

class EarningData(BaseModel):
    date: str
    eps_actual: str
    eps_estimate: str
    revenue_actual: str
    revenue_estimate: str

class TimeBasedData(BaseModel):
    low: str
    high: str
    percentage: str

class StockRequest(BaseModel):
    ticker: str
    sector: str
    isxticker: Optional[bool] = False

class StockUpdateRequest(BaseModel):
    oldTicker: str
    ticker: Optional[str] = None
    sector: str
    isxticker: Optional[bool] = False

class StockDeleteRequest(BaseModel):
    ticker: str

class EnhancedStockData(BaseModel):
    ticker: str
    sector: str
    isxticker: bool
    market_cap: str
    earning_date: str
    current_price: str
    today: TimeBasedData
    previous_day: TimeBasedData
    five_day: TimeBasedData
    one_month: TimeBasedData
    six_month: TimeBasedData
    one_year: TimeBasedData
    ah_percentage: str

class SectorRequest(BaseModel):
    sector: str

class SectorUpdateRequest(BaseModel):
    oldSector: str
    newSector: str

class SectorDeleteRequest(BaseModel):
    sector: str

class UserRequest(BaseModel):
    username: str
    password: str
    role: str
    firstname: str
    lastname: str

class UserUpdateRequest(BaseModel):
    oldUsername: str
    username: str
    password: Optional[str] = ""
    role: str
    firstname: str
    lastname: str

class UserDeleteRequest(BaseModel):
    username: str 