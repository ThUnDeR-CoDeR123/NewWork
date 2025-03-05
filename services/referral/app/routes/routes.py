from fastapi import APIRouter, FastAPI, HTTPException, Path, Depends, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from app.routes.utils import generate_referral_code, get_admin_user,get_normal_user,getTokenDataFromAuthService
from typing import Annotated
from app.database import get_db
from sqlalchemy.orm import Session
from app.crud import create_referral,getReferrers,getUserById,generatetreeChild,generatetreeParent,credit_parent_wallets,update_counts,reward_users_based_on_milestones, getTransactionByMeta
from app.schemas import CreateReferralRequest, ReferralAddRequest,TokenData,UserFilter
from app.crud import addReferral,get_level_counts,generate_tree_with_user_details,getUserByEmail
from sqlalchemy.exc import OperationalError
import traceback



router = APIRouter(prefix="/api/v1/referral")

@router.get("/health")
async def health():
    return {'status':"OK"}

#Create Referral Code
@router.post("/create")
async def create_referral_code(request: CreateReferralRequest, db: Annotated[Session, Depends(get_db)]):
    """
    Generates a unique referral code using a hashing algorithm (e.g., SHA-256) and associates it with the user.
    """
    try :

        code = generate_referral_code(request.user_id)
        user = addReferral(request.user_id,code,db)
    except OperationalError as e:
        JSONResponse(content={"message":"Database error occured, Please try after some time."},status_code=500)

    return JSONResponse(content={"referral_code":user.referral_code},status_code=200)


# Add Referral on Signup
@router.post("/add")
async def add_referral(request: ReferralAddRequest, referral : Annotated[dict, Depends(create_referral)]):
    """
    Adds a referral entry when a user provides a referral code during sign-up.
    Validates the referral code and stores the referred user’s details.
    """
    return JSONResponse(content={"referral_data":referral},status_code=200)


# 3. Get Referral Details
@router.post("/user")
async def get_referral_details(data: UserFilter,   db : Annotated[Session, Depends(get_db)] ):
    print("called")
    try:
        if not data.token_data.is_admin:
            return JSONResponse(status_code=401, content={"message":"Unauthorized access"})
            
        user = getUserByEmail(email=data.email,db=db)
        if not user:
                print("User not found")
                return JSONResponse(status_code=404, content={"message":"user not found"})
        data =generate_tree_with_user_details(db,user.id)

        return data
    except Exception as e:
        raise HTTPException(status_code=500, content={"message": "something went wrong,Please try again!",
                                                      "error":str(e)})

@router.post("/deposit/{user_id}")
async def process_deposit(user_id: int):
    pass 


@router.get("/levels")
async def get_referral_levels():
    pass 


@router.get("/rewards/{user_id}")
async def get_total_earned_rewards(user_id: int ):
    pass 



@router.put("/settings")
async def update_referral_settings():
    """
    Allows administrators to update the referral percentages for each level.
    """
    pass  

# Get Referrers of a User
@router.get("/referrers/{user_id}")
async def get_referrers(user_id: int , db : Annotated[Session, Depends(get_db)], token : TokenData):
    try:
        if not token.is_admin:
            return JSONResponse(status_code=401, content={"message":"Unauthorized access"})
        referrers = await getReferrers(user_id, db)
        if not referrers:
            print("not found")
            return JSONResponse(status_code=404, content={"message":"No referrers found for the given user ID"})
        return {"user_id": user_id, "referrers": referrers}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message":"Something went worng, Please try again!",
                                                      "error":str(e)}) 
  

@router.get("/hierarchy-count/{user_id}")
async def get_hierarchy_count(db: Annotated[Session , Depends(get_db)],user_id: int, max_depth: Optional[int] = 12):
    """
    Retrieves the total number of referred users within a hierarchy for a specified user.
    """
    try:
        # Check if the user exists
        user = getUserById(user_id,db)

        # Generate the referral tree
        referral_tree = generatetreeChild(db, root_user_id=user_id, max_depth=max_depth)

        # Count the total number of referred users
        total_referrals = len(referral_tree)

        # Build the response
        return JSONResponse(
            content={
                "user_id": user_id,
                "total_referrals": total_referrals,
                "max_depth": max_depth,
                "details": referral_tree
            },
            status_code=200
        )

    except OperationalError as e:
        # Return a 500 error in case of database operational errors
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )
    
@router.get("/referral/level-count")
async def get_referral_level_count(
    token: TokenData,
    db: Session = Depends(get_db)
):
    """
    Returns the referral count for each level for a specific user using the referral_count table.
    """
    # return {"data":"none"}
    user_id = token.id
    try:
        # Get level counts using the separate function
        level_counts = get_level_counts(db, user_id)

        if not level_counts:
            return JSONResponse(
                content={"message": f"No referral data found for user_id {user_id}."},
                status_code=404
            )

        # Format the response
        response = [{"level": level, "count": count} for level, count in level_counts]

        return JSONResponse(content=response, status_code=200)

    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )
@router.get("/admin/level-count/{user_id}")
async def get_referral_level_count(
    user_id:int,
    token: TokenData,
    db: Session = Depends(get_db)
):
    """
    Returns the referral count for each level for a specific user using the referral_count table.
    """
    if not token.is_admin :
        return JSONResponse(status_code=401, content={"error":"Unauthorized access"})
    try:
        # Get level counts using the separate function
        level_counts = get_level_counts(db, user_id)

        if not level_counts:
            return JSONResponse(
                content={"message": f"No referral data found for user_id {user_id}."},
                status_code=404
            )

        # Format the response
        response = [{"level": level, "count": count} for level, count in level_counts]
        total_count = sum(count for _, count in level_counts)
        return JSONResponse(content={ "hierarchy_count": total_count, "level_count":response}, status_code=200)

    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@router.get("/hierarchy/calculate-and-credit")
async def calculate_and_credit_parent_hierarchy(
    user_id: int,
    base_amount: float,
    db: Session = Depends(get_db)
):
    """
    Calculate and credit referral amounts for a given user's parent hierarchy,
    update referral counts, and reward users based on milestones.

    :param user_id: The user whose hierarchy is being credited.
    :param base_amount: The base amount for referral rewards.
    :param db: Database session.
    :return: JSON response.
    """
    try:
        # Check if the user exists
        user = getUserById(user_id,db)

        # Generate the parent hierarchy
        print(1)
        parent_hierarchy = generatetreeParent(db, user_id)
        print(2)
        if not parent_hierarchy:
            return JSONResponse(
                content={"message": "No parent hierarchy found for the user."},
                status_code=200
            )
        print(parent_hierarchy)
        for parent in parent_hierarchy:
            print(parent)

        t = getTransactionByMeta(str(user_id),db)

        # parent_hierarchy = [{"referrer_id": row[0], "level": row[1]} for row in parent_hierarchy]

        # Credit referral wallets for the parent hierarchy
        total_credited = credit_parent_wallets(parent_hierarchy, user_id,base_amount, db)

        # Increment referral counts in the referral_count table
        if not t:
            update_counts(db,parent_hierarchy)

        # Reward users who have reached milestones
        reward_users_based_on_milestones(db)

        # Return the success response
        return JSONResponse(
            content={
                "message": "Referral amounts credited successfully.",
                "user_id": user_id,
                "total_credited_amount": total_credited
            },
            status_code=200
        )

    except OperationalError as e:
        return JSONResponse(
            content={"error": f"Database error: {str(e)}"},
            status_code=500
        )
    except Exception as e:
        # Capture the full traceback details
        error_details = traceback.format_exc()
        return JSONResponse(
            content={
                "error": str(e),
                "details": error_details  # Include the full traceback in the response
            },
            status_code=500
        )
