class ReaderError(Exception):
    """Base error; never implies a failed write is safe to retry."""


class ProtocolError(ReaderError):
    pass


class TransportError(ReaderError):
    pass


class DeviceError(ReaderError):
    def __init__(self, command, status, data=b""):
        self.command, self.status, self.data = command, status, data
        super().__init__(f"Command 0x{command:02X}: device status 0x{status:02X}")


class RestoreError(ReaderError):
    def __init__(self, action_succeeded, cause):
        self.action_succeeded = action_succeeded
        self.cause = cause
        super().__init__("Antenna restore failed; action_succeeded=" + str(action_succeeded)
                         + ". Check reader state before continuing; do not retry a write blindly.")
