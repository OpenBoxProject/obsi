class ControlError(Exception):
    """
    Base exception class for control errors
    """
    pass


class UnknownHandlerOperation(Exception):
    """
    Returned when an operation's type is unknown in a sequence of operations.
    """
    pass


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