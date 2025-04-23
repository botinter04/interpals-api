from fastapi import FastAPI, HTTPException, Depends, Header
from typing import Optional
from pydantic import BaseModel
from .job.job_configurations import REDIS_JOB_BASE_KEY, SearchOptions, JobConfigRequest
from .store.store import redis_client
from .job.job_configurations import add_cron_job, count_cron_jobs, get_cron_jobs
from uuid import uuid4
from .lib.session import Session
from .api import ApiAsync

SESSION_EXPIRE_TIME = 7200  # todo- find out how long interpal's sessions typically last and ajust this value accordingly


app = FastAPI(title="Interpals API", description="API for Interpals social network")

class LoginRequest(BaseModel):
    username: str
    password: str

class MessageRequest(BaseModel):
    thread_id: str
    message: str

class FriendRequest(BaseModel):
    uid: str

# Session dependency
async def get_api(x_auth_token: str = Header(..., alias="x-auth-token")) -> ApiAsync:
    """
    Dependency that retrieves the ApiAsync instance using a session from Redis
    """
    data = redis_client.get(f"session:{x_auth_token}")
    
    if not data:
        raise HTTPException(status_code=401, detail="Not authenticated or session expired")
    
    session = Session(data["username"], data["session_id"], data["csrf_cookie"])
    
    return ApiAsync(session)

@app.post("/login")
async def login(request: LoginRequest):
    # I should encrypt the password with a key for security before pushing, frontend will send encrypted key which will be decrypted here.
    session = Session.login(request.username, request.password)
    api = ApiAsync(session)
    try:
        authenticated = await api.check_auth()
        if authenticated:
            token = str(uuid4())
            session_credentials = {"username": session.username, "session_id": session.interpals_sessid, "csrf_cookie": session.csrf_cookieV2}
            redis_client.set(
                f"session:{token}", 
                (session_credentials),
                SESSION_EXPIRE_TIME,
            )
            
            return {
                "status": "success", 
                "message": "Logged in successfully",
                "token": token
            }
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@app.get("/profile/{username}")
async def get_profile(username: str, api: ApiAsync = Depends(get_api)):
    try:
        profile_data = await api.profile(username)
        return profile_data
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Profile error: {str(e)}")

@app.get("/visitors")
async def get_visitors(api: ApiAsync = Depends(get_api)):
    try:
        visitors = await api.visitors()
        return {"visitors": visitors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting visitors: {str(e)}")

@app.post("/search")
async def search(options: SearchOptions, api: ApiAsync = Depends(get_api)):
    try:
        # Convert to dict for the API
        options_dict = options.model_dump(exclude_none=True)
        limit = options_dict.pop("limit", 1000)
        timeout = options_dict.pop("timeout", 0.0)
        
        # Search is an async generator, so we need to collect results
        results = []
        async for user in api.search(options_dict, limit=limit, timeout=timeout):
            results.append(user)
            
        return {"users": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.get("/view/{username}")
async def view_profile(username: str, api: ApiAsync = Depends(get_api)):
    try:
        await api.view(username)
        return {"status": "success", "message": f"Viewed profile of {username}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"View error: {str(e)}")

@app.get("/chats")
async def get_chats(count: int = 9, offset: int = 0, api: ApiAsync = Depends(get_api)):
    try:
        chats = await api.chat(count=count, offset=offset)
        return chats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting chats: {str(e)}")

@app.get("/chat/{thread_id}")
async def get_chat_messages(
    thread_id: str, 
    last_msg_id: Optional[str] = None, 
    api: ApiAsync = Depends(get_api)
):
    try:
        messages = await api.chat_messages(thread_id, last_msg_id)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting messages: {str(e)}")

@app.post("/chat/send")
async def send_message(request: MessageRequest, api: ApiAsync = Depends(get_api)):
    try:
        await api.chat_send(request.thread_id, request.message)
        return {"status": "success", "message": "Message sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")

@app.delete("/chat/{thread_id}")
async def delete_chat(thread_id: str, api: ApiAsync = Depends(get_api)):
    try:
        await api.chat_delete(thread_id)
        return {"status": "success", "message": "Chat deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting chat: {str(e)}")

@app.get("/uid/{username}")
async def get_user_id(username: str, api: ApiAsync = Depends(get_api)):
    try:
        uid = await api.get_uid(username)
        return {"uid": uid}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error getting UID: {str(e)}")

@app.get("/thread/{uid}")
async def get_thread_id(uid: str, api: ApiAsync = Depends(get_api)):
    try:
        thread_id = await api.get_thread_id(uid)
        return {"thread_id": thread_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting thread ID: {str(e)}")

@app.get("/friends/{uid}")
async def get_friends(uid: str, api: ApiAsync = Depends(get_api)):
    try:
        friends = await api.friends(uid)
        return {"friends": friends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting friends: {str(e)}")

@app.post("/friends/add")
async def add_friend(request: FriendRequest, api: ApiAsync = Depends(get_api)):
    try:
        await api.friend_add(request.uid)
        return {"status": "success", "message": "Friend added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding friend: {str(e)}")

@app.post("/friends/remove")
async def remove_friend(request: FriendRequest, api: ApiAsync = Depends(get_api)):
    try:
        await api.friend_remove(request.uid)
        return {"status": "success", "message": "Friend removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing friend: {str(e)}")

@app.get("/albums/{uid}")
async def get_albums(uid: str, api: ApiAsync = Depends(get_api)):
    try:
        albums = await api.albums(uid)
        return {"albums": albums}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting albums: {str(e)}")

@app.get("/pictures/{uid}/{aid}")
async def get_pictures(uid: str, aid: str, api: ApiAsync = Depends(get_api)):
    try:
        pictures = await api.pictures(uid, aid)
        return {"pictures": pictures}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting pictures: {str(e)}")

@app.post("/job")
async def create_job(request: JobConfigRequest, _: ApiAsync = Depends(get_api)):
    name = await add_cron_job(request)
    return {"message": "Job added successfully", "job_name": name}


@app.get("/job")
async def list_jobs(_: ApiAsync = Depends(get_api)):
    job_list = await get_cron_jobs()
    return {"message": "Jobs fetched successfully", "job_list": job_list}

@app.delete("/job/{job_name}")
async def delete_job(job_name: str, _: ApiAsync = Depends(get_api)):
    try:
        redis_client.delete(f"{REDIS_JOB_BASE_KEY}:{job_name}")
        return {"message": f"Job '{job_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")


@app.post("/logout")
async def logout(x_auth_token: str = Header(..., alias="x-auth-token")):
    try:
        redis_client.delete(x_auth_token)
        return {"status": "success", "message": "logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging out: {str(e)}")