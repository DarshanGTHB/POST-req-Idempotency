from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from google.cloud import firestore
from google.oauth2 import service_account
from typing import Optional
import json

app = FastAPI()

# Setup Firebase client
cred = service_account.Credentials.from_service_account_file("firebase_key.json")
db = firestore.Client(credentials=cred, project=cred.project_id)

@app.post("/submit")
async def submit_order(request: Request, idempotency_key: Optional[str] = Header(None)):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Missing Idempotency-Key header")

    doc_ref = db.collection("idempotency").document(idempotency_key)
    doc = doc_ref.get()

    if doc.exists:
        print("Duplicate request. Returning cached response.")
        return JSONResponse(content=doc.to_dict())

    # Simulate processing
    data = await request.json()
    response = {"status": "success", "data": data}

    # Store in Firestore
    doc_ref.set(response)
    return response
