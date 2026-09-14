from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file


class EnvironmentVariablesConstants:

    _mandatory_env_vars = [
        "ENVIRONMENT",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "AWS_ENDPOINT_URL",
        "AWS_SQS_QUALIFY_QUEUE_NAME",
        "AWS_SQS_QUALIFY_DLQ_NAME",
        "AWS_SQS_QUALIFY_QUEUE_URL",
        "AWS_SQS_QUALIFY_DLQ_URL",
        "AWS_SQS_CLASSIFY_QUEUE_NAME",
        "AWS_SQS_CLASSIFY_DLQ_NAME",
        "AWS_SQS_CLASSIFY_QUEUE_URL",
        "AWS_SQS_CLASSIFY_DLQ_URL",
        "CONSUMER_MAX_MESSAGES_PER_REQUEST",
        "CONSUMER_MAX_POOL_TIMEOUT",
        "CONSUMER_MAX_RETRIES",
        "OPENCODE_API_KEY",
        "OPENCODE_DEFAULT_MODEL",
        "OPENCODE_API_URL",
        "OPENCODE_API_MODELS_URL",
        "ASSESSMENT_QUALIFICATION_CHUNK_SIZE",
        "ASSESSMENT_MAX_QUESTIONS_NUMBER",
        "DATABASE_URL",
        "DB_POOL_SIZE",
        "DB_MAX_OVERFLOW",
        "DB_POOL_TIMEOUT",
        "DB_POOL_RECYCLE",
        "DATABASE_ADMIN_USERNAME",
        "DATABASE_ADMIN_PASSWORD",
        "DATABASE_ADMIN_EMAIL",
    ]

    ENVIRONMENT = os.getenv("ENVIRONMENT", "")

    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION = os.getenv("AWS_REGION", "")
    AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "")
    AWS_SQS_QUALIFY_QUEUE_NAME = os.getenv("AWS_SQS_QUALIFY_QUEUE_NAME", "")
    AWS_SQS_QUALIFY_DLQ_NAME = os.getenv("AWS_SQS_QUALIFY_DLQ_NAME", "")
    AWS_SQS_QUALIFY_QUEUE_URL = os.getenv("AWS_SQS_QUALIFY_QUEUE_URL", "")
    AWS_SQS_QUALIFY_DLQ_URL = os.getenv("AWS_SQS_QUALIFY_DLQ_URL", "")
    AWS_SQS_CLASSIFY_QUEUE_NAME = os.getenv("AWS_SQS_CLASSIFY_QUEUE_NAME", "")
    AWS_SQS_CLASSIFY_DLQ_NAME = os.getenv("AWS_SQS_CLASSIFY_DLQ_NAME", "")
    AWS_SQS_CLASSIFY_QUEUE_URL = os.getenv("AWS_SQS_CLASSIFY_QUEUE_URL", "")
    AWS_SQS_CLASSIFY_DLQ_URL = os.getenv("AWS_SQS_CLASSIFY_DLQ_URL", "")
    CONSUMER_MAX_MESSAGES_PER_REQUEST = os.getenv(
        "CONSUMER_MAX_MESSAGES_PER_REQUEST", ""
    )
    CONSUMER_MAX_POOL_TIMEOUT = os.getenv("CONSUMER_MAX_POOL_TIMEOUT", "")
    CONSUMER_MAX_RETRIES = os.getenv("CONSUMER_MAX_RETRIES", "")

    OPENCODE_API_KEY = os.getenv("OPENCODE_API_KEY", "")
    OPENCODE_DEFAULT_MODEL = os.getenv("OPENCODE_DEFAULT_MODEL", "")
    OPENCODE_API_URL = os.getenv("OPENCODE_API_URL", "")
    OPENCODE_API_MODELS_URL = os.getenv("OPENCODE_API_MODELS_URL", "")

    ASSESSMENT_QUALIFICATION_CHUNK_SIZE = os.getenv(
        "ASSESSMENT_QUALIFICATION_CHUNK_SIZE", ""
    )
    ASSESSMENT_MAX_QUESTIONS_NUMBER = os.getenv("ASSESSMENT_MAX_QUESTIONS_NUMBER", "")

    DATABASE_URL = os.getenv("DATABASE_URL", "")
    DB_POOL_SIZE = os.getenv("DB_POOL_SIZE", "")
    DB_MAX_OVERFLOW = os.getenv("DB_MAX_OVERFLOW", "")
    DB_POOL_TIMEOUT = os.getenv("DB_POOL_TIMEOUT", "")
    DB_POOL_RECYCLE = os.getenv("DB_POOL_RECYCLE", "")
    DATABASE_ADMIN_USERNAME = os.getenv("DATABASE_ADMIN_USERNAME", "")
    DATABASE_ADMIN_PASSWORD = os.getenv("DATABASE_ADMIN_PASSWORD", "")
    DATABASE_ADMIN_EMAIL = os.getenv("DATABASE_ADMIN_EMAIL", "")

    @staticmethod
    def validate_mandatory_env_vars():
        for var in EnvironmentVariablesConstants._mandatory_env_vars:
            if not os.getenv(var):
                raise EnvironmentError(
                    f"Mandatory environment variable '{var}' is not set."
                )
