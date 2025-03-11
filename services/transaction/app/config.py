from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str
    algorithm: str
    auth_service_url : str
    referral_service_url : str
    database_url : str
    apiurl : str
    apikey : str



    class Config:
        env_file = ".env"


settings = Settings()


