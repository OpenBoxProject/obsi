class ConnectionError(Exception):
    pass


class ConnectionConfigurationError(ConnectionError):
    pass


class Connection(object):
    """
    A connection between two elements.
    """

    __CONNECTION_PATTERN = "{from_element}[{from_port}]->[{to_port}]{to_element};"

    def __init__(self, from_element, to_element, from_port=0, to_port=0):
        self.from_element = from_element
        self.to_element = to_element
        self.from_port = from_port
        self.to_port = to_port

    @classmethod
    def from_dict(cls, config):
        from_element = config.get("src")
        if from_element is None:
            raise ConnectionConfigurationError("Connection has no 'src' element in configuration")
        to_element = config.get("dst")
        if to_element is None:
            raise ConnectionConfigurationError("Connection has no 'dst' element in configuration")

        try:
            from_port = int(config.get('src_port', '0'))
        except ValueError:
            raise ConnectionConfigurationError("src_port must be an integer")
        try:
            to_port = int(config.get('dst_port', '0'))
        except ValueError:
            raise ConnectionConfigurationError("dst_port must be an integer")

        return cls(from_element, to_element, from_port, to_port)

    def to_click_config(self):
        return self.__CONNECTION_PATTERN.format(from_element=self.from_element, to_element=self.to_element,
                                                from_port=self.from_port, to_port=self.to_port)
