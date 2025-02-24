from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    auth : str # = "http://127.0.0.1:8001/api/v1/auth"
    user : str #= "http://127.0.0.1:8000/api/v1/user"
    referral : str #= "http://127.0.0.1:8002/api/v1/referral"
    transaction : str #= "http://127.0.0.1:8003/api/v1/transaction" 
    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    allowed_origins: str
    # Mail settings
    mail_username: str
    mail_password: str 
    mail_from: str 
    mail_port: int 
    mail_server: str 
    mail_from_name: str 
    mail_starttls: bool 
    mail_ssl_tls: bool 
    use_credentials: bool 
    validate_certs: bool 
    brevo_api_key: str 
    smtp_api_url: str 
    class Config:
        env_file = ".env"


settings = Settings()