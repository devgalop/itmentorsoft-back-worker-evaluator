from contextlib import asynccontextmanager
from common_py_aws import (
    SqsConsumerConfig,
    SqsConsumerService,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from itmentorsoft_persistence import PostgresAssessmentMapper, PostgresQuestionMapper

from src.dependencies import (
    get_cache_service,
    get_classify_message_sanitizer,
    get_classify_service,
    get_model_explorer_service,
    get_model_selector_service,
    get_publisher_service,
    get_qualifier_service,
    get_qualify_message_sanitizer,
)
from src.endpoints.init import router as endpoints_router
from src.infrastructure.broker.aws.aws_sqs_classify_consumer import ClassifyConsumer
from src.infrastructure.broker.aws.aws_sqs_connection_factory import (
    SqsConnectionFactory,
)
from src.infrastructure.broker.aws.aws_sqs_create_queues import SqsCreator
from src.infrastructure.broker.aws.aws_sqs_qualify_consumer import SqsQualifyConsumer
from src.infrastructure.cache.valkey_client import ValkeyClient
from src.infrastructure.databases.postgresql.postgres_classification_repository import (
    PostgresClassificationRepository,
)
from src.infrastructure.databases.postgresql.postgres_qualification_repository import (
    PostgresQualificationRepository,
)
from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants
from src.services.cache_manager_service import CacheManagerService
from src.services.classify_service import ClassifyService
from src.services.qualify_service import QualifyService

DEV_ENVIRONMENT = "dev"
PREFIX_CACHE_QUALIFICATION = "qualification"
PREFIX_CACHE_CLASSIFICATION = "classification"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up the application...")
    print("Validating environment variables...")
    EnvironmentVariablesConstants.validate_mandatory_env_vars()

    print("Initializing the cache service...")
    cache_client = ValkeyClient()
    await cache_client.connect()

    app.state.valkey = cache_client
    print("Cache service initialized.")

    print("Loading available models...")
    cache_service = get_cache_service(client=cache_client)
    model_selector_service = get_model_selector_service(cache_service=cache_service)
    model_explorer_service = get_model_explorer_service(cache_service=cache_service)
    await model_explorer_service.get_available_models()
    print("Available models loaded.")

    print("Creating SQS connection...")
    sqs_connection = SqsConnectionFactory.create_sqs_client()
    if EnvironmentVariablesConstants.ENVIRONMENT == DEV_ENVIRONMENT:
        sqs_creator = SqsCreator(sqs_connection)
        sqs_creator.create_queues()

    print("SQS connection established.")

    sqs_qualify_consumer = SqsConsumerService(
        sqs_client=sqs_connection,
        sqs_config=SqsConsumerConfig(
            queue_url=EnvironmentVariablesConstants.AWS_SQS_QUALIFY_QUEUE_URL,
            max_messages=int(
                EnvironmentVariablesConstants.CONSUMER_MAX_MESSAGES_PER_REQUEST
            ),
            wait_time_seconds=int(
                EnvironmentVariablesConstants.CONSUMER_MAX_POOL_TIMEOUT
            ),
            is_enabled=True,
            max_retries=int(EnvironmentVariablesConstants.CONSUMER_MAX_RETRIES),
            dlq_url=EnvironmentVariablesConstants.AWS_SQS_QUALIFY_DLQ_URL,
            visibility_timeout_seconds=int(
                EnvironmentVariablesConstants.CONSUMER_MESSAGES_VISIBILITY_TIMEOUT
            ),
        ),
        sqs_handler=SqsQualifyConsumer(
            get_qualify_message_sanitizer(),
            QualifyService(
                qualification_repository_factory=lambda session: PostgresQualificationRepository(
                    session, PostgresAssessmentMapper, PostgresQuestionMapper
                ),
                qualifier_service=await get_qualifier_service(
                    model_selector_service=model_selector_service,
                    cache_service=cache_service,
                ),
                model_selector_service=model_selector_service,
                model_explorer_service=model_explorer_service,
                cache_service=CacheManagerService(
                    PREFIX_CACHE_QUALIFICATION, cache_service
                ),
                publisher_service=get_publisher_service(sqs_client=sqs_connection),
            ),
        ),
    )

    sqs_classify_consumer = SqsConsumerService(
        sqs_client=sqs_connection,
        sqs_config=SqsConsumerConfig(
            queue_url=EnvironmentVariablesConstants.AWS_SQS_CLASSIFY_QUEUE_URL,
            max_messages=int(
                EnvironmentVariablesConstants.CONSUMER_MAX_MESSAGES_PER_REQUEST
            ),
            wait_time_seconds=int(
                EnvironmentVariablesConstants.CONSUMER_MAX_POOL_TIMEOUT
            ),
            is_enabled=True,
            max_retries=int(EnvironmentVariablesConstants.CONSUMER_MAX_RETRIES),
            dlq_url=EnvironmentVariablesConstants.AWS_SQS_CLASSIFY_DLQ_URL,
            visibility_timeout_seconds=int(
                EnvironmentVariablesConstants.CONSUMER_MESSAGES_VISIBILITY_TIMEOUT
            ),
        ),
        sqs_handler=ClassifyConsumer(
            get_classify_message_sanitizer(),
            ClassifyService(
                classification_repository_factory=lambda session: PostgresClassificationRepository(
                    session, PostgresAssessmentMapper
                ),
                cache_service=CacheManagerService(
                    PREFIX_CACHE_CLASSIFICATION, cache_service
                ),
                classification_service=await get_classify_service(
                    model_selector_service=model_selector_service,
                    cache_service=cache_service,
                ),
                model_explorer_service=model_explorer_service,
                model_selector_service=model_selector_service,
                publisher_service=get_publisher_service(sqs_client=sqs_connection),
            ),
        ),
    )
    app.state.sqs_consumers = {
        "qualify": sqs_qualify_consumer,
        "classify": sqs_classify_consumer,
    }
    sqs_qualify_consumer.start_consumer()
    sqs_classify_consumer.start_consumer()
    print("SQS consumer started.")
    yield
    print("Shutting down the application...")
    await sqs_qualify_consumer.stop_consumer()
    await sqs_classify_consumer.stop_consumer()
    print("SQS consumer stopped.")
    print("Application shutdown complete.")


app = FastAPI(lifespan=lifespan)

app.include_router(endpoints_router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": 500,
            "message": "An unexpected error occurred",
            "path": request.url.path,
        },
    )
