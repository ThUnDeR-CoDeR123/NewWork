from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database and service URLs
    database_url: str 
    auth_service_url: str 
    referral_service_url: str
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


print(f"Database URL: {settings.database_url}")
# print(f"Auth Service URL: {settings.auth_service_url}")
# print(f"Referral Service URL: {settings.referral_service_url}")