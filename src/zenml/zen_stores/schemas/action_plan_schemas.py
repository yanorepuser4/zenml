#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""SQL Model Implementations for Action Plans."""
import json
from datetime import datetime
from typing import List, TYPE_CHECKING
from uuid import UUID

from pydantic import Field
from pydantic.json import pydantic_encoder
from sqlalchemy import Column, String
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import Relationship

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.models import (
    ActionPlanRequest,
    ActionPlanResponse,
    ActionPlanResponseBody,
    ActionPlanUpdate,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.trigger_schemas import TriggerSchema


class ActionPlanSchema(BaseSchema, table=True):
    """SQL Model for tag."""

    __tablename__ = "action_plan"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="action_plans")

    flavor: str = Field(nullable=False)

    configuration: str = Field(
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        )
    )

    triggers: List["TriggerSchema"] = Relationship(back_populates="action_plan")



    @classmethod
    def from_request(cls, request: ActionPlanRequest) -> "ActionPlanSchema":
        """Convert an `ActionPlanRequest` to an `ActionPlanSchema`.

        Args:
            request: The request model to convert.

        Returns:
            The converted schema.
        """
        # TODO: complete this
        return cls(
            flavor=request.flavor,
            configuration=json.dumps(
                request.configuration,
                sort_keys=False,
                default=pydantic_encoder,
            ),
        )

    def to_model(self, hydrate: bool = False) -> ActionPlanResponse:
        """Convert an `ActionPlanSchema` to an `ActionPlanResponse`.

        Args:
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The created `TagResponse`.
        """
        # TODO: complete this
        return ActionPlanResponse(
            id=self.id,
            body=ActionPlanResponseBody(
                created=self.created,
                updated=self.updated
            ),
        )

    def update(self, update: ActionPlanUpdate) -> "ActionPlanSchema":
        """Updates a `ActionPlanSchema` from a `ActionPlanUpdate`.

        Args:
            update: The `ActionPlanUpdate` to update from.

        Returns:
            The updated `TagSchema`.
        """
        for field, value in update.dict(exclude_unset=True).items():
            setattr(self, field, value)
        self.updated = datetime.utcnow()
        return self