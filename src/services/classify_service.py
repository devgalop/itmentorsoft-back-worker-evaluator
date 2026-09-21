from common_py_aws import PublisherService, SqsPublisherService
from itmentorsoft_persistence.repositories import ClassificationRepository

from src.contracts.cache_service import CacheService
from src.contracts.classification_service import ClassificationService
from src.contracts.qualifier_service import ModelExplorerService, ModelSelectorService
from src.infrastructure.broker.aws.aws_sqs_connection_factory import (
    SqsConnectionFactory,
)


class ClassifyService:

    def __init__(self):
        self.classification_repository: ClassificationRepository | None = None
        self.qualifier_service: ClassificationService | None = None
        self.model_selector_service: ModelSelectorService | None = None
        self.model_explorer_service: ModelExplorerService | None = None
        self.cache_service: CacheService | None = None
        self.publisher_service: PublisherService = SqsPublisherService(
            SqsConnectionFactory.create_sqs_client()
        )
