#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

class ConfigurationError(Exception):
    """
    The base class for all errors related for building a full configuration or any of its parts.
    """
    pass


class EngineConfigurationError(ConfigurationError):
    pass


class EngineElementConfigurationError(ConfigurationError):
    pass


class ClickBlockConfigurationError(EngineConfigurationError):
    pass


class ClickElementConfigurationError(EngineConfigurationError):
    pass


class ConnectionConfigurationError(ConfigurationError):
    pass


class OpenBoxBlockConfigurationError(ConfigurationError):
    pass


class OpenBoxConfigurationError(ConfigurationError):
    pass


class ClickModuleTranslationError(EngineConfigurationError):
    pass