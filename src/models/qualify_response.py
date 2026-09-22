class QualifyResponse:
    def __init__(self, is_success: bool, message: str = ""):
        self.is_success = is_success
        self.message = message
