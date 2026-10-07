import json

from common_py_aws import PublishMessageRequest

from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants


class ClassificationNotifyRequest:
    def __init__(self, user_id: str, classification: str, feedback: str):
        self.user_id = user_id
        self.classification = classification
        self.feedback = feedback


class NotificationResponse:
    def __init__(self, is_success: bool, message: str):
        self.is_success = is_success
        self.message = message


class NotificationMessageVariables:
    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def to_dict(self) -> dict[str, str]:
        return {"key": self.key, "value": self.value}

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class NotificationMessage(PublishMessageRequest):

    def __init__(
        self,
        recipient: str,
        subject: str,
        html_template_code: str,
        message_variables: list[NotificationMessageVariables],
    ):
        self.recipient = recipient
        self.subject = subject
        self.html_template_code = html_template_code
        self.message_variables = message_variables

    def get_url(self) -> str:
        return EnvironmentVariablesConstants.AWS_SQS_NOTIFY_QUEUE_URL

    def get_message(self) -> str:
        return self.to_json()

    def to_dict(self) -> dict[str, str | list[dict[str, str]]]:
        return {
            "recipient": self.recipient,
            "subject": self.subject,
            "html_template_code": self.html_template_code,
            "message_variables": [mv.to_dict() for mv in self.message_variables],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
