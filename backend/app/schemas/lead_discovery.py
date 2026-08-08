from pydantic import BaseModel, Field

class LeadDiscoveryRequest(BaseModel):
    location: str = Field(min_length=1, max_length=255)
    work_mode: str = Field(min_length=1, max_length=50)
    batch_size: int = Field(ge=1, le=50, default=5)
