import os
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn
from dotenv import load_dotenv

load_dotenv()

RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY")  
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY") 

if not RECAPTCHA_SITE_KEY or not RECAPTCHA_SECRET_KEY:
    raise RuntimeError("Set RECAPTCHA_SITE_KEY and RECAPTCHA_SECRET_KEY in environment.")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return "ok"

@app.get("/sitekey")
async def get_sitekey():
    return {"sitekey": RECAPTCHA_SITE_KEY}


async def verify_token_with_google(token: str, remote_ip: str | None = None) -> dict:
    url = "https://www.google.com/recaptcha/api/siteverify"
    data = {"secret": RECAPTCHA_SECRET_KEY, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip

    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(url, data=data)
        r.raise_for_status()
        return r.json()


@app.post("/verify")
async def verify_recaptcha(request: Request, g_recaptcha_response: str = Form(..., alias="g-recaptcha-response")):
    """
    Verifies the reCAPTCHA token sent from the frontend.
    Returns Google's verification response JSON to the client.
    """
    token = g_recaptcha_response
    print("Request JSON:", {"g-recaptcha-response": token})
    if not token:
        raise HTTPException(status_code=400, detail="Missing recaptcha token.")

    remote_ip = None
    try:
        remote_ip = request.client.host
    except Exception:
        remote_ip = None

    google_resp = await verify_token_with_google(token, remote_ip=remote_ip)
    print("Google Response JSON:", google_resp)

    if not google_resp.get("success", False):
        return JSONResponse(status_code=400, content={"ok": False, "google": google_resp})

    print("Verification successful for token:", token)
    return JSONResponse(status_code=200, content={"ok": True, "google": google_resp})

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)