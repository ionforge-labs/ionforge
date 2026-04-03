"""Custom base model for generated code.

Configures ``populate_by_name=True`` so that generated models accept
both the camelCase alias and the snake_case field name.
"""

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
