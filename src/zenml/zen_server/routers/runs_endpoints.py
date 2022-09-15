#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Endpoint definitions for pipeline runs."""
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from zenml.constants import (
    COMPONENT_SIDE_EFFECTS,
    GRAPH,
    RUNS,
    RUNTIME_CONFIGURATION,
    STEPS,
    VERSION_1,
)
from zenml.models.pipeline_models import PipelineRunModel, StepRunModel
from zenml.utils.uuid_utils import parse_optional_name_or_uuid
from zenml.zen_server.auth import authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=VERSION_1 + RUNS,
    tags=["runs"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "/",
    response_model=List[PipelineRunModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def get_runs(
    project_name_or_id: Optional[str] = None,
    stack_id: Optional[str] = None,
    pipeline_id: Optional[str] = None,
) -> List[PipelineRunModel]:
    """Get pipeline runs according to query filters.

    Args:
        project_name_or_id: Name or ID of the project for which to filter runs.
        stack_id: ID of the stack for which to filter runs.
        pipeline_id: ID of the pipeline for which to filter runs.

    Returns:
        The pipeline runs according to query filters.
    """
    return zen_store.list_runs(
        project_name_or_id=parse_optional_name_or_uuid(project_name_or_id),
        stack_id=stack_id,
        pipeline_id=pipeline_id,
    )


@router.get(
    "/{run_id}",
    response_model=PipelineRunModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def get_run(run_id: str) -> PipelineRunModel:
    """Get a specific pipeline run using its ID.

    Args:
        run_id: ID of the pipeline run to get.

    Returns:
        The pipeline run.
    """
    return zen_store.get_run(run_id=UUID(run_id))


@router.delete(
    "/{run_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def delete_run(run_id: str) -> None:
    """Delete a pipeline run using its ID.

    Args:
        run_id: ID of the pipeline run to get.
    """
    zen_store.delete_run(run_id=UUID(run_id))


@router.get(
    "/{run_id}" + GRAPH,
    response_model=str,  # TODO: Use file type / image type
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def get_run_dag(
    run_id: str,
) -> FileResponse:  # TODO: use file type / image type
    """Get the DAG for a given pipeline run.

    Args:
        run_id: ID of the pipeline run to use to get the DAG.

    Returns:
        The DAG for a given pipeline run.
    """
    image_object_path = zen_store.get_run_dag(
        run_id=UUID(run_id)
    )  # TODO: ZenStore should return a path
    return FileResponse(image_object_path)


@router.get(
    "/{run_id}" + STEPS,
    response_model=List[StepRunModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def get_run_steps(run_id: str) -> List[StepRunModel]:
    """Get all steps for a given pipeline run.

    Args:
        run_id: ID of the pipeline run to use to get the DAG.

    Returns:
        The steps for a given pipeline run.
    """
    return zen_store.list_run_steps(UUID(run_id))


# TODO: Figure out what exactly gets returned from this
@router.get(
    "/{run_id}" + RUNTIME_CONFIGURATION,
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_run_runtime_configuration(run_id: str) -> Dict:
    """Get the runtime configuration for a given pipeline run.

    Args:
        run_id: ID of the pipeline run to use to get the runtime configuration.

    Returns:
        The runtime configuration for a given pipeline run.
    """
    return zen_store.get_run_runtime_configuration(run_id=UUID(run_id))


@router.get(
    "/{run_id}" + COMPONENT_SIDE_EFFECTS,
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
async def get_run_component_side_effects(
    run_id: str, component_id: str
) -> Dict:
    """Get the component side-effects for a given pipeline run.

    Args:
        run_id: ID of the pipeline run to use to get the component side-effects.
        component_id: ID of the component to use to get the component
            side-effects.

    Returns:
        The component side-effects for a given pipeline run.
    """
    return zen_store.get_run_component_side_effects(
        run_id=UUID(run_id),
        component_id=component_id,
    )
