from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os

app = FastAPI(title="Mock Peppol Provider")

@app.get("/provider/invoices")
async def get_invoices():
    # Return list of invoice XML content from files in /invoices directory
    invoices = []
    invoice_dir = os.path.join(os.path.dirname(__file__), "invoices")
    for filename in sorted(os.listdir(invoice_dir)):
        if filename.endswith(".xml"):
            with open(os.path.join(invoice_dir, filename)) as f:
                invoices.append({
                    "filename": filename,
                    "xml_content": f.read()
                })
    return JSONResponse({"invoices": invoices})
