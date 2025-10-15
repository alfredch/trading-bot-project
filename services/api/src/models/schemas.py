"""
API Schemas - Request/Response models
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class MigrationJobRequest(BaseModel):
    """Migration job request - ANGEPASST für TimescaleDB"""
    run_id: int = Field(..., description="Run ID", example=10)
    instrument_id: int = Field(..., description="Instrument ID", example=643)
    start_date: str = Field(..., description="Start date (ISO format)", example="2023-01-02")
    end_date: str = Field(..., description="End date (ISO format)", example="2023-01-03")
    chunk_size: Optional[int] = Field(1000000, description="Chunk size for processing")


class BacktestJobRequest(BaseModel):
    """Backtest job request"""
    strategy_name: str = Field(..., example="mean_reversion_nw")
    run_id: int = Field(..., example=10)
    instrument_id: int = Field(..., example=643)
    start_date: str = Field(..., example="2023-01-02")
    end_date: str = Field(..., example="2023-01-03")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class JobResponse(BaseModel):
    """Job response"""
    job_id: str
    status: str
    message: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    redis: str
    timestamp: str