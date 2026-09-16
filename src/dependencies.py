from src.contracts.message_sanitizer import MessageSanitizer
from src.services.classify_message_sanitizer import ClassifyMessageSanitizer
from src.services.qualify_message_sanitizer import QualifyMessageSanitizer


def get_qualify_message_sanitizer() -> MessageSanitizer:
    return QualifyMessageSanitizer()


def get_classify_message_sanitizer() -> MessageSanitizer:
    return ClassifyMessageSanitizer()
