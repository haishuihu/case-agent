from pydantic import BaseModel, Field


class ModelOption(BaseModel):
    key: str
    label: str
    provider: str
    model_name: str = Field(alias="modelName")
    supports_vision: bool = Field(alias="supportsVision")
    supports_structured_output: bool = Field(alias="supportsStructuredOutput")

    model_config = {"populate_by_name": True}
