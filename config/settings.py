"""
Configuration settings for REMB Optimization Engine
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "REMB - Industrial Estate Master Planning Engine"
    VERSION: str = "0.1.0"
    
    # Database Settings
    POSTGRES_USER: str = "remb_user"
    POSTGRES_PASSWORD: str = "remb_password"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "remb_db"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Optimization Settings
    NSGA2_POPULATION_SIZE: int = 100
    NSGA2_GENERATIONS: int = 200
    NSGA2_CROSSOVER_RATE: float = 0.9
    NSGA2_MUTATION_RATE: float = 0.1
    
    # MILP Solver Settings
    MILP_TIME_LIMIT_SECONDS: int = 3600  # 1 hour
    MILP_SOLVER: str = "SCIP"  # OR-Tools solver
    
    # File Upload Settings
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list = [".shp", ".dxf", ".geojson"]
    
    # Processing Settings
    MAX_CONCURRENT_OPTIMIZATIONS: int = 2
    CELERY_BROKER_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
