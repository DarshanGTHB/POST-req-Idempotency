from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
from google.cloud import firestore
from google.oauth2 import service_account

class Order(BaseModel):
    product: str
    qty: int

app = FastAPI()

# Initialize Firestore
cred = service_account.Credentials.from_service_account_file("firebase_key.json")
db = firestore.Client(credentials=cred, project=cred.project_id)

@app.get("/", response_class=HTMLResponse)
async def form():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Order Form with Idempotency</title>
        <style>
            body {
                font-family: Arial;
                margin: 2rem;
                background: #f8f9fa;
            }
            label {
                font-weight: bold;
            }
            input {
                padding: 6px;
                margin: 5px 0;
            }
            button {
                margin-top: 10px;
                padding: 8px 15px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            button:hover {
                background: #0056b3;
            }
            pre {
                margin-top: 20px;
                padding: 1rem;
                background: #e9ecef;
                border-radius: 5px;
                overflow-x: auto;
            }
        </style>
    </head>
    <body>
        <h2>🛒 Place an Order</h2>
        <form id="orderForm">
            <label for="product">Product:</label><br>
            <input type="text" id="product" name="product" required><br><br>
            <label for="qty">Quantity:</label><br>
            <input type="number" id="qty" name="qty" required><br><br>
            <button type="submit">Submit</button>
        </form>
        <button onclick="resetState()">🔄 Reset Simulation</button>

        <pre id="result"></pre>

        <script>
            const form = document.getElementById("orderForm");
            const resultEl = document.getElementById("result");

            let lastPayload = null;
            let lastKey = null;

            function log(msg, data = null) {
                resultEl.textContent += `\\n${msg}`;
                if (data) {
                    resultEl.textContent += `\\n${JSON.stringify(data, null, 2)}\\n`;
                }
            }

            function resetState() {
                lastKey = null;
                lastPayload = null;
                resultEl.textContent = "🔄 State reset. Ready for new order.";
            }

            form.addEventListener("submit", async function (e) {
                e.preventDefault();
                resultEl.textContent = "";  // Clear logs

                const product = document.getElementById("product").value.trim();
                const qty = parseInt(document.getElementById("qty").value);
                const payload = { product, qty };

                if (JSON.stringify(payload) === JSON.stringify(lastPayload)) {
                    log("🔁 Duplicate order detected, reusing last idempotency key:");
                } else {
                    lastKey = crypto.randomUUID();
                    lastPayload = payload;
                    log("🆕 New order detected, generated idempotency key:");
                }

                log(lastKey);
                log("📦 Sending payload:", payload);

                try {
                    const res = await fetch("/submit", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "Idempotency-Key": lastKey
                        },
                        body: JSON.stringify(payload)
                    });

                    const data = await res.json();
                    log("✅ Server Response:", data);

                    if (res.status === 200) {
                        log("🟢 Request succeeded!");
                    } else {
                        log(`🟡 Warning: Received status ${res.status}`);
                    }
                } catch (err) {
                    log("🔴 Error occurred:", err);
                }
            });
        </script>
    </body>
    </html>
    """

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

    response = {"status": "success", "data": order.dict()}
    doc_ref.set(response)
    return response
