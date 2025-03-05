from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas import  UserUpdate, User,DeleteUser,updateWalletId,TokenData,UserFilter
from app.database import get_db
from app.crud.user import updateUser,getUserById,truncateUsersTable,deleteUser,getAllUsers,deleteAllTable,truncateUserTable,updateUserWalletid,get_level_counts,generatetreeChild
from typing import Annotated,List
from app.routes.utils import oauth2_scheme,getTokenDataFromAuthService,modelToSchema
from starlette.responses import JSONResponse
import json
import traceback
from sqlalchemy import text
from app.config import settings
import httpx
import time
tokenRouter = APIRouter(prefix="/api/v1/user")

#get user data
@tokenRouter.get("/me", response_model=User)
async def read_user(token_data: TokenData | None,db: Annotated[Session, Depends(get_db)]):
    print(token_data)
    # token_da  ta = await getTokenDataFromAuthService(token)
    if token_data is None :
        return JSONResponse(status_code=401,content={"message": "missing Authorization header"})
    if token_data.flag != "LOGIN":
        print(token_data)
        return JSONResponse(status_code=401,content={"message": "Invalid Credentials!"})
    user = getUserById(token_data.id,db)

   
    user1 =modelToSchema(user,db=db)

    
    h_count=0
    for i in user1.level_count:
        h_count+=i["count"]
        print(h_count,i["count"])
    user1.hierarchy_count = h_count
           
    return user1

    


#get all user
@tokenRouter.post("/all", response_model=List[User])
async def read_user_all(filter: UserFilter | None,db: Annotated[Session, Depends(get_db)]):
    start = time.time()
    
    # token_data = await getTokenDataFromAuthService(token)
    token_data = filter.token_data
    
    if token_data is None :
        return JSONResponse(status_code=401,content={"message": "missing Authorization header"})
    print("for auth : ",time.time()-start,"s")
    start = time.time()
    #need to add isadmin check
    if token_data.flag != "LOGIN":
        return JSONResponse(status_code=401,content={"message":"Invalid Credentials!"})
    user = getUserById(token_data.id,db)
    if user.is_admin :

        users=getAllUsers(db,filter)
        print("for fetching : ",time.time()-start,"s")
        
        return users
    return JSONResponse(status_code=401,content={"message":"Permission Denied!"})



#Update user
@tokenRouter.put("/update", response_model=User)
async def update_user(db: Annotated[Session, Depends(get_db)],user: UserUpdate):
    # token_data = await getTokenDataFromAuthService(token)
    token_data = user.token_data
    if token_data is None :
        return JSONResponse(status_code=401,content={"message": "missing Authorization header"})

    if token_data.flag != "LOGIN":
        return JSONResponse(status_code=401,content={"message":"Invalid Credentials!"})

    updated_user = updateUser(
                            user_id=token_data.id,
                            user= user,
                            db=db)  # Use the ID from the current user
    return modelToSchema(updated_user)



@tokenRouter.put("/update/walletid")
async def update_user_wallet(db: Annotated[Session, Depends(get_db)],wallet: updateWalletId):


    # token_data = await getTokenDataFromAuthService(token)

    token_data = wallet.token_data
    
    if token_data is None :
        return JSONResponse(status_code=401,content={"message": "missing Authorization header"})
    if token_data.flag != "LOGIN":
        return JSONResponse(status_code=401,content={"message":"Invalid Credentials!"})
    updated_user = updateUserWalletid(user_id=token_data.id,wallet_id=wallet.wallet_id,db=db)  # Use the ID from the current user
    if not updated_user:
            return JSONResponse(status_code=401,content={'message': "Couldn't update wallet id"})
    # except Exception as e:
    #     error_details = traceback.format_exc()  # Captures the full stack trace
    #     return JSONResponse(status_code=400, content={"error": str(e), "details": error_details})
    return JSONResponse(status_code=200,content={"message":"wallet_updated successfully!"})



# Delete user
@tokenRouter.delete("/delete",response_model=DeleteUser)
async def delete_user(token_data: TokenData | None,db: Annotated[Session, Depends(get_db)]):
    # token_data = await getTokenDataFromAuthService(token)
    if token_data is None :
        return JSONResponse(status_code=401,content={"message": "missing Authorization header"})
    if token_data.flag != "LOGIN":
        return JSONResponse(status_code=401,content={"message":"Invalid Credentials!"})
    deleted_user=deleteUser(token_data.id,db)
    return DeleteUser(msg = "User deleted successfully", username=deleted_user.email)



#truncate user table
@tokenRouter.delete("/users/truncate")
def drop_user(msg : Annotated[dict, Depends(truncateUsersTable)],msg1 : Annotated[dict, Depends(truncateUserTable)]):
    return msg

@tokenRouter.delete("/tables/drop")
def drop_user(msg : Annotated[bool, Depends(deleteAllTable)]):
    if msg:
        return {'msg': "dropped all tables successfully!"}
    


TABLE_NAMES = [
    "users",
    "entitlement",
    "cryptowallet",
    "referralwallet",
    "referrals",
    "transactions"
]
 


@tokenRouter.get("/schemas")
async def get_model_table_schemas(db: Session = Depends(get_db)):
    """
    Get schema information for hardcoded tables from the models and display it clustered by table.
    """
    try:
        # SQL query to get column information for specified tables
        query = text("""
            SELECT 
                table_schema, 
                table_name, 
                column_name, 
                data_type, 
                is_nullable, 
                character_maximum_length
            FROM information_schema.columns
            WHERE table_name = ANY(:table_names)
            ORDER BY table_name, ordinal_position;
        """)

        # Execute the query
        result = db.execute(query, {"table_names": TABLE_NAMES}).mappings()
        clustered_schemas = {}

        # Process the query results to cluster by table name
        for row in result:
            table_name = row["table_name"]
            column_info = {
                "column_name": row["column_name"],
                "data_type": row["data_type"],
                "is_nullable": row["is_nullable"],
                "character_max_length": row["character_maximum_length"]
            }
            if table_name not in clustered_schemas:
                clustered_schemas[table_name] = {
                    "table_schema": row["table_schema"],
                    "columns": []
                }
            clustered_schemas[table_name]["columns"].append(column_info)

        # Convert clustered schemas to a list for JSON response
        formatted_response = [
            {"table_name": table, "schema": schema}
            for table, schema in clustered_schemas.items()
        ]

        # Return the clustered schemas as JSON
        return JSONResponse(status_code=200, content={"schemas": formatted_response})

    except Exception as e:
        # Capture and return detailed exception
        error_details = traceback.format_exc()
        return JSONResponse(status_code=500, content={"error": str(e), "details": error_details})