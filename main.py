from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from google.cloud import firestore
from google.oauth2 import service_account

class Order(BaseModel):
    product: str
    qty: int

app = FastAPI()

# Initialize Firestore (as before)…
cred = service_account.Credentials.from_service_account_file("firebase_key.json")
db = firestore.Client(credentials=cred, project=cred.project_id)

@app.post("/submit")
async def submit_order(
    order: Order,
    idempotency_key: Optional[str] = Header(None),
):
    if not idempotency_key:
        raise HTTPException(400, "Missing Idempotency-Key header")

    doc_ref = db.collection("idempotency").document(idempotency_key)
    doc = doc_ref.get()

    if doc.exists:
        return JSONResponse(content=doc.to_dict())

    # order is already validated and parsed
    response = {"status": "success", "data": order.dict()}

    # store in Firestore
    doc_ref.set(response)
    return response
