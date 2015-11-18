from exceptions import OpenBoxConfigurationError
from open_box_blocks import OpenBoxBlock
from connection import Connection


class OpenBoxConfiguration(object):
    def __init__(self, requirements=None, blocks=None, connections=None):
        self.requirements = requirements or []
        self.blocks = blocks or []
        self.connections = connections or []
        self._blocks_by_name = dict((block.name, block) for block in self.blocks)

    def block_by_name(self, name):
        return self._blocks_by_name.get(name, None)

    @classmethod
    def from_dict(cls, config, additional_requirements=None):
        requirements = additional_requirements or []
        requirements.extend(config['requirements'])
        blocks = [OpenBoxBlock.from_dict(block_config) for block_config in config['blocks']]
        block_names = set(block.name for block in blocks)
        connections = []
        for connection_config in config['connections']:
            connection = Connection.from_dict(connection_config)
            if connection.src not in block_names:
                raise OpenBoxConfigurationError(
                    "{src} in connection's source block is undefined".format(src=connection.src))
            if connection.dst not in block_names:
                raise OpenBoxConfigurationError(
                    "{dst} in connection's dest block is undefined".format(dst=connection.dst))
            connections.append(connection)

        return cls(requirements, blocks, connections)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (self.requirements == other.requirements and
                self.blocks == other.blocks and
                self.connections == other.connections)

    def __ne__(self, other):
        return not self.__eq__(other)
