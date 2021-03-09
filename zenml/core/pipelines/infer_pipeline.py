#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os
from typing import Dict, Text, Any, List
from typing import Optional

import tensorflow as tf
from tfx.components.common_nodes.importer_node import ImporterNode
from tfx.components.schema_gen.component import SchemaGen
from tfx.components.statistics_gen.component import StatisticsGen
from tfx.types import standard_artifacts

from zenml.core.backends.orchestrator import OrchestratorBaseBackend
from zenml.core.components.bulk_inferrer.component import BulkInferrer
from zenml.core.components.data_gen.component import DataGen
from zenml.core.datasources import BaseDatasource
from zenml.core.metadata import ZenMLMetadataStore
from zenml.core.pipelines import BasePipeline
from zenml.core.repo import ArtifactStore
from zenml.core.standards import standard_keys as keys
from zenml.core.standards.standard_keys import StepKeys
from zenml.core.steps import BaseStep
from zenml.core.steps.inferrer import BaseInferrer
from zenml.utils import path_utils
from zenml.utils.enums import GDPComponent
from zenml.utils.post_training.post_training_utils import \
    convert_raw_dataset_to_pandas
from zenml.utils.post_training.post_training_utils import \
    view_statistics, view_schema, get_feature_spec_from_schema


class BatchInferencePipeline(BasePipeline):
    """BatchInferencePipeline definition to run batch inference pipelines.

    A BatchInferencePipeline is used to run an inference based on a
    TrainingPipeline.
    """
    PIPELINE_TYPE = 'infer'

    def __init__(self,
                 model_uri: Text,
                 name: Text = None,
                 enable_cache: Optional[bool] = True,
                 steps_dict: Dict[Text, BaseStep] = None,
                 backend: OrchestratorBaseBackend = None,
                 metadata_store: Optional[ZenMLMetadataStore] = None,
                 artifact_store: Optional[ArtifactStore] = None,
                 datasource: Optional[BaseDatasource] = None,
                 pipeline_name: Optional[Text] = None):
        """
        Construct a Batch Inference pipeline. This is a pipeline that allows
        for offline batch inference.

        Args:
            name: Outward-facing name of the pipeline.
            model_uri: URI for a model, usually generated by
            TrainingPipeline and retrieved by
            `training_pipeline.get_model_uri()`.
            labels: List of labels to be predicted by the model.
            pipeline_name: A unique name that identifies the pipeline after
             it is run.
            enable_cache: Boolean, indicates whether or not caching
             should be used.
            steps_dict: Optional dict of steps.
            backend: Orchestrator backend.
            metadata_store: Configured metadata store. If None,
             the default metadata store is used.
            artifact_store: Configured artifact store. If None,
             the default artifact store is used.
        """
        if model_uri is None:
            raise AssertionError('model_uri cannot be None.')
        self.model_uri = model_uri
        super(BatchInferencePipeline, self).__init__(
            name=name,
            enable_cache=enable_cache,
            steps_dict=steps_dict,
            backend=backend,
            metadata_store=metadata_store,
            artifact_store=artifact_store,
            datasource=datasource,
            pipeline_name=pipeline_name,
            model_uri=model_uri,
        )

    def get_tfx_component_list(self, config: Dict[Text, Any]) -> List:
        """
        Creates an inference pipeline out of TFX components.

        A inference pipeline is used to run a batch of data through a
        ML model via the BulkInferrer TFX component.

        Args:
            config: Dict. Contains a ZenML configuration used to build the
             data pipeline.

        Returns:
            A list of TFX components making up the data pipeline.
        """
        component_list = []

        data_config = \
            config[keys.GlobalKeys.PIPELINE][keys.PipelineKeys.STEPS][
                keys.InferSteps.DATA]
        data = DataGen(
            name=self.datasource.name,
            source=data_config[StepKeys.SOURCE],
            source_args=data_config[StepKeys.ARGS]).with_id(
            GDPComponent.DataGen.name)
        component_list.extend([data])

        # Handle timeseries
        # TODO: [LOW] Handle timeseries
        # if GlobalKeys. in train_config:
        #     schema = ImporterNode(instance_name='Schema',
        #                           source_uri=spec['schema_uri'],
        #                           artifact_type=standard_artifacts.Schema)
        #
        #     sequence_transform = SequenceTransform(
        #         examples=data.outputs.examples,
        #         schema=schema,
        #         config=train_config,
        #         instance_name=GDPComponent.SequenceTransform.name)
        #     datapoints = sequence_transform.outputs.output
        #     component_list.extend([schema, sequence_transform])

        # Load from model_uri
        model = ImporterNode(
            instance_name=GDPComponent.Trainer.name,
            source_uri=self.model_uri,
            artifact_type=standard_artifacts.Model)

        model_result = model.outputs.result

        infer_cfg = config[keys.GlobalKeys.PIPELINE][keys.PipelineKeys.STEPS][
            keys.InferSteps.INFER]

        bulk_inferrer = BulkInferrer(
            source=infer_cfg[StepKeys.SOURCE],
            source_args=infer_cfg[StepKeys.ARGS],
            model=model_result,
            examples=data.outputs.examples,
            instance_name=GDPComponent.Inferrer.name)

        statistics = StatisticsGen(
            examples=bulk_inferrer.outputs.predictions
        ).with_id(GDPComponent.DataStatistics.name)

        schema = SchemaGen(
            statistics=statistics.outputs.output,
        ).with_id(GDPComponent.DataSchema.name)

        component_list.extend([model, bulk_inferrer, statistics, schema])

        return component_list

    def add_infer_step(self, infer_step: BaseInferrer):
        self.steps_dict[keys.InferSteps.INFER] = infer_step

    def steps_completed(self) -> bool:
        mandatory_steps = [keys.InferSteps.DATA, keys.InferSteps.INFER]
        for step_name in mandatory_steps:
            if step_name not in self.steps_dict.keys():
                raise AssertionError(
                    f'Mandatory step {step_name} not added.')
        return True

    def view_statistics(self, magic: bool = False):
        """
        View statistics for infer pipeline in HTML.

        Args:
            magic (bool): Creates HTML page if False, else
            creates a notebook cell.
        """
        uri = self.get_artifacts_uri_by_component(
            GDPComponent.DataStatistics.name)[0]
        view_statistics(uri, magic)

    def view_schema(self):
        """View schema of data flowing in pipeline."""
        uri = self.get_artifacts_uri_by_component(
            GDPComponent.DataSchema.name)[0]
        view_schema(uri)

    def get_predictions(self, sample_size: int = 100000):
        """
        Samples prediction data as a pandas DataFrame.

        Args:
            sample_size: # of rows to sample.
        """
        base_uri = self.get_artifacts_uri_by_component(
            GDPComponent.Inferrer.name)[0]
        data_files = path_utils.list_dir(os.path.join(base_uri, 'examples'))
        dataset = tf.data.TFRecordDataset(data_files, compression_type='GZIP')
        schema_uri = self.get_artifacts_uri_by_component(
            GDPComponent.DataSchema.name)[0]
        spec = get_feature_spec_from_schema(schema_uri)
        return convert_raw_dataset_to_pandas(dataset, spec, sample_size)
