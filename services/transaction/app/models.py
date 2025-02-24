from typing import List
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import json







class Base(DeclarativeBase):
    def to_dict(self, seen=None):
        if seen is None:
            seen = set()
        if self in seen:
            return {}  # Prevent infinite loop by returning an empty dict for already seen objects.
        seen.add(self)
        data = {column.name: (
            getattr(self, column.name).isoformat() if isinstance(getattr(self, column.name), datetime) else getattr(self, column.name)
        ) for column in self.__table__.columns}

        # Handle relationships if any
        for rel_name in self.__mapper__.relationships.keys():
            related_obj = getattr(self, rel_name)
            if related_obj is not None:
                if isinstance(related_obj, list):  # One-to-many relationship
                    data[rel_name] = [item.to_dict(seen=seen) for item in related_obj]
                else:  # Many-to-one or one-to-one relationship
                    data[rel_name] = related_obj.to_dict(seen=seen)

        return data

    # Convert SQLAlchemy model instance to JSON string
    def to_json(self):
        return json.dumps(self.to_dict(), default=str)  # Use default=str to handle datetime serialization







class Entitlement(Base):
    __tablename__ = "entitlement"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(30))
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    del_flag: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
 
    def __repr__(self) -> str:
        return f"Entitlement(id={self.id!r}, label={self.label!r})"



class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    wallet_id: Mapped[str] = mapped_column(String, nullable=True,unique= True)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    otp : Mapped[str] = mapped_column(String, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_code: Mapped[Optional[str]] = mapped_column(String, nullable=False)
    del_flag: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    transaction_id: Mapped[Optional[str]] = mapped_column(String, nullable=True,unique=True) 


    #Relationships
    interim_wallet = relationship("InterimWallet", back_populates="user", uselist=False, cascade="all, delete")
    entitlements: Mapped[List[Entitlement]] = relationship("Entitlement", backref="user", lazy='select')
    crypto_wallet: Mapped["CryptoWallet"] = relationship("CryptoWallet", back_populates="user", uselist=False, cascade="all, delete")
    referral_wallet: Mapped["ReferralWallet"] = relationship("ReferralWallet", back_populates="user", uselist=False, cascade="all, delete")
    referred_users: Mapped[List["Referral"]] = relationship(
        "Referral",
        back_populates="referrer",
        foreign_keys="Referral.referred_user_id",
        cascade="all, delete"
    )
    referrer_users: Mapped[List["Referral"]] = relationship(
        "Referral",
        back_populates="referred_user",
        foreign_keys="Referral.referrer_id" ,
        cascade="all, delete"
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, email={self.email!r})"

   



class CryptoWallet(Base):
    __tablename__ = "cryptowallet"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), unique=True)  # Foreign key to user
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    deposit_amt: Mapped[float] = mapped_column(Float, nullable=True)
    del_flag: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
  
    # Optional relationship to User if required
    user: Mapped["User"] = relationship("User", back_populates="crypto_wallet", uselist=False, cascade="all, delete")

    def __repr__(self) -> str:
        return f"CryptoWallet(id={self.id!r}, user_id={self.user_id!r}, balance={self.balance!r}, deposit_amt={self.deposit_amt!r})"
    


class ReferralWallet(Base):
    __tablename__ = "referralwallet"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), unique=True)  # Foreign key to user
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    del_flag: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
 
    # Optional relationship to User if required
    user: Mapped["User"] = relationship("User", back_populates="referral_wallet", uselist=False, cascade="all, delete")

    def __repr__(self) -> str:
        return f"ReferralWallet(id={self.id!r}, user_id={self.user_id!r}, balance={self.balance!r})"
    

class InterimWallet(Base):
    __tablename__ = "interimwallet"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), unique=True)  # Foreign key to user
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    del_flag: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Optional relationship to User if required
    user: Mapped["User"] = relationship("User", back_populates="interim_wallet", uselist=False, cascade="all, delete")

    def __repr__(self) -> str:
        return f"InterimWallet(id={self.id!r}, user_id={self.user_id!r}, balance={self.balance!r})"

class AdminWallet(Base):
    __tablename__ = "adminwallet"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_id: Mapped[str] = mapped_column(String, nullable=False,unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    del_flag: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[int] = mapped_column(Integer, default=0)  # 0 for Inactive, 1 for Active
    def __repr__(self) -> str:
        return f"AdminWallet(id={self.id!r}, wallet_id={self.wallet_id!r}, balance={self.balance!r})"
    
    
    
    
class Referral(Base):
    __tablename__ = 'referrals'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    referrer_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    referred_user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    del_flag: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    referrer: Mapped["User"] = relationship("User",foreign_keys=[referrer_id], back_populates="referrer_users", uselist=False, cascade="all, delete")
    referred_user: Mapped["User"] = relationship("User", foreign_keys=[referred_user_id], back_populates="referred_users", uselist=False, cascade="all, delete")
        
    def __repr__(self) -> str:
        return (
            f"<Referral(id={self.id}, "
            f"referrer_id={self.referrer_id}, "
            f"referred_user_id={self.referred_user_id}, "
            f"created_at='{self.created_at}')>"
        )
    

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_id: Mapped[str] = mapped_column(String,nullable=False)  
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    transaction_type: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 for credit, 1 for debit
    ammount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    status: Mapped[int] = mapped_column(Integer, default=0)  # 0 for pending, 1 for completed, -1 for failed
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))  # User who created the transaction , basically an admin
    meta: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    transaction_id: Mapped[Optional[str]] = mapped_column(String, nullable=True,unique=True)  # Nullable, refers to a hash rate ID if applicable
    from_type: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 for hash, 1 for referral
    
    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], backref="user_transactions")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], backref="created_transactions")

    def __repr__(self) -> str:
        return (
            f"Transaction(id={self.id}, wallet_id={self.wallet_id}, user_id={self.user_id}, "
            f"transaction_type={self.transaction_type}, amount={self.amount}, status={self.status})"
        )

class ReferralCount(Base):
    __tablename__ = "referral_count"
    # Fields
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)  # Primary Key
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)  # Foreign Key to User
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # Referral Level
    count: Mapped[int] = mapped_column(Integer, nullable=False)  # Count of referrals at this level

    # Relationships
    user: Mapped["User"] = relationship("User", backref="referral_counts", lazy="select")

    def __repr__(self) -> str:
        return (
            f"<ReferralCount(id={self.id}, user_id={self.user_id}, level={self.level}, count={self.count})>"
        )