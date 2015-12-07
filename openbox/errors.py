#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

import traceback
from cStringIO import StringIO
from manager_exceptions import (ManagerError, EngineNotRunningError, ProcessingGraphNotSetError)
from configuration_builder.configuration_builder_exceptions import (ClickBlockConfigurationError,
                                                                    ClickElementConfigurationError,
                                                                    ConfigurationError,
                                                                    ConnectionConfigurationError,
                                                                    EngineConfigurationError,
                                                                    EngineElementConfigurationError,
                                                                    OpenBoxBlockConfigurationError,
                                                                    OpenBoxConfigurationError)


class ErrorType:
    BAD_REQUEST = 'BAD_REQUEST'
    FORBIDDEN = 'FORBIDDEN'
    UNSUPPORTED = 'UNSUPPORTED'
    INTERNAL_ERROR = 'INTERNAL_ERROR'


class ErrorSubType:
    # BAD_REQUEST
    BAD_VERSION = 'BAD_VERSION'
    BAD_TYPE = 'BAD_TYPE'
    BAD_GRAPH = 'BAD_GRAPH'
    BAD_BLOCK = 'BAD_BLOCK'
    BAD_CONNECTOR = 'BAD_CONNECTOR'
    BAD_HEADER_MATCH = 'BAD_HEADER_MATCH'
    BAD_PAYLOAD_MATCH = 'BAD_PAYLOAD_MATCH'
    BAD_FILE = 'BAD_FILE'
    ILLEGAL_ARGUMENT = 'ILLEGAL_ARGUMENT'
    ILLEGAL_STATE = 'ILLEGAL_STATE'

    # FORBIDDEN
    NOT_PERMITTED = 'NOT_PERMITTED'
    NO_ACCESS = 'NO_ACCESS'

    # UNSUPPORTED
    UNSUPPORTED_VERSION = 'UNSUPPORTED_VERSION'
    UNSUPPORTED_BLOCK = 'UNSUPPORTED_BLOCK'
    UNSUPPORTED_MESSAGE = 'UNSUPPORTED_MESSAGE'
    UNSUPPORTED_OTHER = 'UNSUPPORTED_OTHER'

    # INTERNAL
    ADD_MODULE_FAILED = 'ADD_MODULE_FAILED'
    INTERNAL_ERROR = 'INTERNAL_ERROR'


def _traceback_string(exc_tb):
    tb_file = StringIO()
    traceback.print_tb(exc_tb, file=tb_file)
    return tb_file.getvalue()


def exception_to_error_args(exc_type, exc_value, exc_tb):
    error_type = ErrorType.INTERNAL_ERROR
    error_subtype = ErrorSubType.INTERNAL_ERROR
    exception_message = exc_value.message or "General internal error"
    extended_message = _traceback_string(exc_tb)

    if exc_type == EngineNotRunningError:
        exception_message = "Engine is not running"
    elif exc_type == ProcessingGraphNotSetError:
        error_type = ErrorType.BAD_REQUEST
        error_subtype = ErrorSubType.ILLEGAL_STATE
        exception_message = "Processing graph is not set"
    elif exc_type in (EngineElementConfigurationError, ClickElementConfigurationError, ClickBlockConfigurationError,
                      OpenBoxBlockConfigurationError):
        error_type = ErrorType.BAD_REQUEST
        error_subtype = ErrorSubType.BAD_BLOCK
    elif exc_type == ConnectionConfigurationError:
        error_type = ErrorType.BAD_REQUEST
        error_subtype = ErrorSubType.BAD_CONNECTOR
    elif exc_type in (OpenBoxConfigurationError, EngineConfigurationError, ConfigurationError):
        error_type = ErrorType.BAD_REQUEST
        error_subtype = ErrorSubType.BAD_GRAPH

    return error_type, error_subtype, exception_message, extended_message

