class ManagerError(Exception):
    pass


class EngineNotRunningError(ManagerError):
    pass


class ProcessingGraphNotSetError(ManagerError):
    pass
