class ControlError(Exception):
    """
    Base exception class for control errors
    """
    message = "Error in engine control client"


class UnknownHandlerOperation(ControlError):
    """
    Returned when an operation's type is unknown in a sequence of operations.
    """
    message = "Unknown operation type for handler"


class ControlSyntaxError(ControlError):
    """
    500
    """
    pass


class UnimplementedCommandError(ControlError):
    """
    501
    """
    pass


class NoSuchHandlerError(ControlError):
    """
    511
    """
    pass


class HandlerError(ControlError):
    """
    520
    """
    pass


class PermissionDeniedError(ControlError):
    """
    530
    """
    pass


class NoRouterInstalledError(ControlError):
    """
    540
    """
    pass


class NoSuchElementError(ControlError):
    """
    510
    """
    pass