from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.kms_router import kms_router
from routers.aes_router import aes_router

import logging

import os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(
    title="S3 File Manager API",
    description="Unified API for S3 file management with AES-256 and KMS encryption",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(aes_router, prefix="/aes")
app.include_router(kms_router, prefix="/kms")

@app.on_event("startup")
async def startup_event():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("API Server Started")
    print("""
==========================================
🔐 S3 File Manager API - FastAPI
📍 Encryption Methods:
  • AES-256-CBC: /aes/*
  • AWS KMS: /kms/*
==========================================
""")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000)