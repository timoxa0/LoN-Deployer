class FastbootException(Exception):
    def __init__(self, message, output):
        super().__init__(message)
        self.output = output


class UnauthorizedBootImage(FastbootException):
    pass


class DeviceNotFound(Exception):
    pass


class RepartitonError(Exception):
    pass


class UnsupportedPlatform(Exception):
    def __init__(self, platform):
        super().__init__(f"{platform} is not supported")
        self.platform = platform
