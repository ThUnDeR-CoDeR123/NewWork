from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
from sqlalchemy.exc import NoResultFound
from app.models import Referral, User  , ReferralCount,ReferralWallet,Transaction
from typing import Annotated
from app.schemas import ReferralAddRequest
from fastapi import HTTPException, Depends
from app.database import get_db

def create_referral(request: ReferralAddRequest, db: Annotated[Session,Depends(get_db)]):
    """
    Adds a referral entry when a user provides a referral code during sign-up.
    Validates the referral code and stores the referred user’s details.
    """
    
    referrer = db.query(User).filter(User.referral_code == request.referrer_code).first()
    if not referrer:
        raise ValueError(f"Invalid referral code: {request.referrer_code}")

   
    referred_user = db.query(User).filter(User.id == request.referred_user_id).first()
    if not referred_user:
        raise ValueError(f"Invalid referred user ID: {request.referred_user_id}")

   
    existing_referral = (
        db.query(Referral)
        .filter(Referral.referrer_id == referrer.id, Referral.referred_user_id == request.referred_user_id)
        .first()
    )
    if existing_referral:
        raise ValueError(f"Referral already exists between referrer ID {referrer.id} and referred user ID {request.referred_user_id}")
    

    
    new_referral = Referral(
        referrer_id=referrer.id,
        referred_user_id=request.referred_user_id,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_referral)  
    db.commit()  
    db.refresh(new_referral)

    return new_referral.to_dict()
    
async def getReferrers(user_id: int, db: Session):
    
    referral_entries = (
        db.query(Referral)
        .filter(Referral.referred_user_id == user_id)
        .all()
    )
    print(1)
    referrer_details = []
    for referral in referral_entries:
        referrer = referral.referrer  # Using the relationship to access the referrer object
        if referrer:
            referrer_details.append({
                "referrer_id": referrer.id,
                "referrer_email": referrer.email,
                "referrer_full_name": referrer.full_name,
                "referral_created_at": referral.created_at.isoformat()
            })
    print(2)
    print(referrer_details)
    return referrer_details

def getUserById(id: int, db: Session ):
    db_user = db.query(User).filter(User.id == id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User does not exists")
    return db_user


def addReferral(id: int, referral_code: str, db: Session):
    # Fetch the user by ID
    db_user = getUserById(id, db)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if referral_code is already set
    if db_user.referral_code is None or db_user.referral_code =="":
        db_user.referral_code = referral_code
        db.commit()
        db.refresh(db_user)
        return db_user
    else:
        return db_user  # Return user if referral_code already exists

def credit_parent_wallets(parent_hierarchy,user_id:int, base_amount: float, db: Session) -> float:
    """
    Credits referral wallets for users in the parent hierarchy.

    :param parent_hierarchy: List of parents in the hierarchy with levels.
    :param base_amount: Base amount used for calculating the rewards.
    :param db: Database session.
    :return: Total amount credited across all wallets.
    """
    total_credited = 0.0

    for parent in parent_hierarchy:
        referrer_id = parent["referrer_id"]  # Parent user ID
        level = parent["depth"]             # Level in the hierarchy

        # Calculate the reward for this level
        reward_amount = calculate_credit_amount(level, base_amount)
        if reward_amount <= 0:
            continue

        # Fetch the referrer's wallet
        referral_wallet = db.query(ReferralWallet).filter(ReferralWallet.user_id == referrer_id).first()
        if not referral_wallet:
            # Skip if the referral wallet doesn't exist for this user
            continue

        # Credit the wallet
        if createTransaction(referrer_id,str(user_id),reward_amount,db ):
            updateOrCreateReferralWallet(referrer_id,reward_amount,db)
            total_credited += reward_amount
        else:
            print("existing transaction with meta as user id is already there!")

    # Commit the transaction
    db.commit()
    return total_credited



def credit_user_account(user_id: int, amount: float, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if not user.referral_wallet:
            raise Exception("User does not have a referral wallet")
        user.referral_wallet.balance += amount
        db.commit()

def reward_users_based_on_milestones(db: Session):
    """
    Checks for users who have reached referral milestones and rewards them accordingly.

    :param db: Database session.
    """
    milestones = {
        0: {"count": 10, "amount": 25},     # entry
        1: {"count": 100, "amount": 300},     # Mercury
        2: {"count": 500, "amount": 600},     # Venus
        3: {"count": 2000, "amount": 1000},   # Earth
        4: {"count": 5000, "amount": 3000},   # Mars
        5: {"count": 12000, "amount": 5000},  # Jupiter
        6: {"count": 25000, "amount": 8000},  # Saturn
        7: {"count": 40000, "amount": 12000}, # Uranus
        8: {"count": 60000, "amount": 20000}  # Neptune
    }

    # Iterate through the milestones
    for level, milestone in milestones.items():
        required_count = milestone["count"]
        reward_amount = milestone["amount"]
        if level == 0:
            level = 1
        # Find users who meet the milestone count at the given level
        users_to_reward = db.query(ReferralCount).filter(
            ReferralCount.level == level,
            ReferralCount.count == required_count
        ).all()

        for user_referral in users_to_reward:
            user_id = user_referral.user_id

            # Fetch the user's referral wallet
            meta = "USER"+str(user_id)+"LEVEL"+str(level)+"COUNT"+str(required_count)
            existingTransaction = db.query(Transaction).filter(Transaction.meta == meta).first()
            user = getUserById(user_id,db)
            # Credit the reward amount
            if not existingTransaction:
                newTransaction = Transaction(
                    wallet_id=user.wallet_id,
                    user_id=user_id,
                    transaction_type=0,  # Assuming 0 for credit
                    ammount=round(reward_amount, 2),
                    created_at=datetime.now(timezone.utc),
                    status=0,  # Assuming 0 for pending
                    from_type=1,  # Assuming 1 for referral
                    meta=meta
                )
                db.add(newTransaction)
                print(f"Transaction with ID {newTransaction.id} created successfully." , meta)
                
            

    # Commit the transaction
    db.commit()

def calculate_credit_amount(level: int, base_amount: float) -> float:
    reward_percentages = {
        1: 10.00,
        2: 5.00,
        3: 3.00,
        4: 2.00,
        5: 1.00,
        6: 0.50,
        7: 0.50,
        8: 0.50,
        9: 0.25,
        10: 0.25,
        11: 0.25,
        12: 0.25,
    }
    percentage = reward_percentages.get(level, 0)
    return (base_amount * percentage) / 100




def generatetreeParent(db_session: Session, root_user_id: int, max_depth: int = 12):
    """
    Generate a referral tree starting from a specific user, traversing up the hierarchy.

    :param db_session: SQLAlchemy database session
    :param root_user_id: The user ID to start building the referral tree
    :param max_depth: Maximum depth for the referral tree
    :return: List of dictionaries representing the referral tree
    """
    query = text("""
        WITH RECURSIVE referral_tree AS (
            -- Base case: start from the leaf node (specific referred_user_id)
            SELECT 
                r.id AS referral_id,
                r.referrer_id,
                r.referred_user_id,
                1 AS depth
            FROM referrals r
            WHERE r.referred_user_id = :root_user_id  -- Starting point (leaf node)

            UNION ALL

            -- Recursive case: find the parent (referrer) for the current node
            SELECT 
                r.id AS referral_id,
                r.referrer_id,
                r.referred_user_id,
                rt.depth + 1 AS depth
            FROM referrals r
            INNER JOIN referral_tree rt ON r.referred_user_id = rt.referrer_id
            WHERE rt.depth < :max_depth  AND r.del_flag = FALSE-- Limit depth to max_depth
        )
        SELECT * FROM referral_tree;
    """)

    # Execute the query with parameters
    result = db_session.execute(query, {"root_user_id": root_user_id, "max_depth": max_depth})

    # Use fetchall() to get all rows
    rows = result.fetchall()

    # Convert result rows to a list of dictionaries
    tree = [{"referral_id": row[0], "referrer_id": row[1], "referred_user_id": row[2], "depth": row[3]} for row in rows]
    
    return tree


def generate_tree_with_user_details(db_session: Session, root_user_id: int, max_depth: int = 12):
    query = text("""
        WITH RECURSIVE referral_tree AS (
            SELECT 
                r.id AS referral_id,
                r.referrer_id,
                r.referred_user_id,
                1 AS depth
            FROM referrals r
            WHERE r.referrer_id = :root_user_id AND r.del_flag = FALSE

            UNION ALL

            SELECT 
                r.id AS referral_id,
                r.referrer_id,
                r.referred_user_id,
                rt.depth + 1 AS depth
            FROM referrals r
            INNER JOIN referral_tree rt ON r.referrer_id = rt.referred_user_id
            WHERE rt.depth < :max_depth AND r.del_flag = FALSE
        )
        SELECT 
            rt.referral_id,
            rt.referrer_id,
            referrer_user.full_name AS referrer_name,
            referrer_user.email AS referrer_email,
            rt.referred_user_id,
            referred_user.full_name AS referred_user_name,
            referred_user.email AS referred_user_email,
            rt.depth
        FROM referral_tree rt
        LEFT JOIN users referrer_user ON rt.referrer_id = referrer_user.id
        LEFT JOIN users referred_user ON rt.referred_user_id = referred_user.id;
    """)

    result = db_session.execute(query, {"root_user_id": root_user_id, "max_depth": max_depth})

    # Use fetchall() to get all rows
    rows = result.fetchall()

    # Convert rows to dictionaries
    try:
        # For modern SQLAlchemy versions where rows behave like mappings
        return [dict(row) for row in rows]
    except TypeError:
        # For older SQLAlchemy versions where rows are not directly mappable
        return [
            {
                "referral_id": row[0],
                "referrer_id": row[1],
                "referrer_name": row[2],
                "referrer_email": row[3],
                "referred_user_id": row[4],
                "referred_user_name": row[5],
                "referred_user_email": row[6],
                "depth": row[7],
            }
            for row in rows
        ]

def generatetreeChild(db_session: Session, root_user_id: int, max_depth: int = 12):
    query = text("""
            WITH RECURSIVE referral_tree AS (
                SELECT 
                    r.id AS referral_id,
                    r.referrer_id,
                    r.referred_user_id,
                    1 AS depth
                FROM referrals r
                WHERE r.referrer_id = :root_user_id AND r.del_flag = FALSE

                UNION ALL

                SELECT 
                    r.id AS referral_id,
                    r.referrer_id,
                    r.referred_user_id,
                    rt.depth + 1 AS depth
                FROM referrals r
                INNER JOIN referral_tree rt ON r.referrer_id = rt.referred_user_id
                WHERE rt.depth < :max_depth AND r.del_flag = FALSE
            )
            SELECT * FROM referral_tree;
    """)

    result = db_session.execute(query, {"root_user_id": root_user_id, "max_depth": max_depth})

    # Use fetchall() to get all rows
    rows = result.fetchall()

    # Convert rows to dictionaries
    try:
        # For modern SQLAlchemy versions where rows behave like mappings
        return [dict(row) for row in rows]
    except TypeError:
        # For older SQLAlchemy versions where rows are not directly mappable
        return [
            {"referral_id": row[0], "referrer_id": row[1], "referred_user_id": row[2], "depth": row[3]}
            for row in rows
        ]
def getUserByEmail(email: str, db: Session ):
    db_user = db.query(User).filter(User.email == email, User.del_flag == False).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found or has been marked as deleted")
    return db_user
# Function to update the ReferralCount table
def update_counts(db_session: Session, referral_tree: list):
    """
    Update the count column in the ReferralCount table based on the referral tree.

    :param db_session: SQLAlchemy database session
    :param referral_tree: List of referral tree data with referrer_id and depth
    """
    for node in referral_tree:
        referrer_id = node['referrer_id']
        level = node['depth']

        # Check if the entry already exists in ReferralCount
        existing_entry = db_session.query(ReferralCount).filter(
            ReferralCount.user_id == referrer_id,
            ReferralCount.level == level
        ).first()

        if existing_entry:
            # Increment the count
            existing_entry.count += 1
        else:
            # Create a new entry
            new_entry = ReferralCount(user_id=referrer_id, level=level, count=1)
            db_session.add(new_entry)
    
    # Commit the transaction
    db_session.commit()
    print("Counts updated successfully.")

def get_level_counts(db: Session, user_id: int):
    """
    Retrieves referral counts by level for a specific user from the referral_count table.
    
    :param db: SQLAlchemy session
    :param user_id: The user ID for which to retrieve referral counts
    :return: List of tuples [(level, count), ...]
    """
    return (
        db.query(ReferralCount.level, ReferralCount.count)
        .filter(ReferralCount.user_id == user_id)
        .all()
    )



def createTransaction( userId: int, user_id:str, amount: float, db: Session):
    # Check if a transaction with the same transaction ID already exists
    # existingTransaction = db.query(Transaction).filter(Transaction.meta == user_id).first()
    
    
    user = getUserById(userId,db)
    # Create a new transaction if no duplicate is found
    newTransaction = Transaction(
        wallet_id=user.wallet_id,
        user_id=userId,
        transaction_type=0,  # Assuming 0 for credit
        ammount=round(amount, 2),
        created_at=datetime.now(timezone.utc),
        status=1,  # Assuming 1 for successful
        from_type=1,  # Assuming 1 for referral
        meta=user_id
    )
    db.add(newTransaction)
    print(f"Transaction with ID {newTransaction.id} created successfully for parent.")
    return newTransaction
    

def getTransactionByMeta(userId: str, db: Session):
    return db.query(Transaction).filter(
            Transaction.meta == userId
        ).first()

def updateOrCreateReferralWallet(userId: int, amount: float, db: Session):
    referralWallet = db.query(ReferralWallet).filter(ReferralWallet.user_id == userId).first()
    if referralWallet:
        referralWallet.balance += amount
    else:
        referralWallet = ReferralWallet(
            user_id=userId,
            balance=amount,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(referralWallet)
