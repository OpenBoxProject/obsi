#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################


class ManagerError(Exception):
    pass


class EngineNotRunningError(ManagerError):
    pass


class ProcessingGraphNotSetError(ManagerError):
    pass


class UnknownRequestedParameter(ManagerError):
    pass


class UnsupportedModuleDataEncoding(ManagerError):
    pass
