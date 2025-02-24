from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url : str
    auth_service_url: str 
    secret_key: str
    algorithm: str 

    class Config:
        env_file = ".env"


settings = Settings()


print(settings.database_url)