class ClickConfiguration(object):
    REQUIREMENTS_PATTERN = 'require(package "{package}");'

    def __init__(self, requirements=None, elements=None, connections=None):
        self.requirements = requirements or []
        self.elements = elements or []
        self.connections = connections or []
        self._elements_by_name = dict((element.name, element) for element in self.blocks)

    def to_engine_config(self):
        config = []
        for requirement in self.requirements:
            config.append(self.REQUIREMENTS_PATTERN.format(package=requirement))

        for element in self.elements:
            config.append(element.to_click_config())

        for connection in self.connections:
            config.append(connection.to_click_config())

        return '\n'.join(config)