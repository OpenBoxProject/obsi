#!/usr/bin/env python
#
# Copyright (c) 2015 Pavel Lazar pavel.lazar (at) gmail.com
#
# The Software is provided WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
#####################################################################

import re
import socket
import collections
import time

from control_exceptions import (UnknownHandlerOperation, ControlError, ControlSyntaxError, HandlerError,
                        NoRouterInstalledError, NoSuchElementError, NoSuchHandlerError, PermissionDeniedError,
                        UnimplementedCommandError)


class ResponseCodes:
    OK = 200
    OK_BUT_WITH_WARNINGS = 220
    SYNTAX_ERROR = 500
    UNIMPLEMENTED_COMMAND = 501
    NO_SUCH_ELEMENT = 510
    NO_SUCH_HANDLER = 511
    HANDLER_ERROR = 520
    PERMISSION_DENIED = 530
    NO_ROUTER_INSTALLED = 540


class Commands:
    READ = 'READ'
    READ_DATA = 'READDATA'
    READ_UNTIL = 'READUNTIL'
    WRITE = 'WRITE'
    WRITE_DATA = 'WRITEDATA'
    WRITE_UNTIL = 'WRITEUNTIL'
    CHECK_READ = 'CHECKREAD'
    CHECK_WRITE = 'CHECKWRITE'
    LLRPC = 'LLRPC'
    QUIT = 'QUIT'


_EXCPTIONS_CODE_MAPPING = {
    ResponseCodes.SYNTAX_ERROR: ControlSyntaxError,
    ResponseCodes.UNIMPLEMENTED_COMMAND: UnimplementedCommandError,
    ResponseCodes.NO_SUCH_ELEMENT: NoSuchElementError,
    ResponseCodes.NO_SUCH_HANDLER: NoSuchHandlerError,
    ResponseCodes.HANDLER_ERROR: HandlerError,
    ResponseCodes.PERMISSION_DENIED: PermissionDeniedError,
    ResponseCodes.NO_ROUTER_INSTALLED: NoRouterInstalledError
}

CONNECT_RETRIES = 50
CHATTER_SOCKET_REGEXP = re.compile(r'ChatterSocket\(.*\)')
CONTROL_SOCKET_REGEXP = re.compile(r'ControlSocket\(.*\)')


class ClickControlClient(object):
    def __init__(self):
        self._socket = None
        self.cotrol_socket_element_name = None
        self.protocol_version = None
        self._buffer = ''
        self.family = None
        self.address = None
        self._socket = None
        self.connected = False

    def connect(self, address, family=socket.AF_INET):
        self.family = family
        self.address = address
        self._socket = socket.socket(family=self.family)
        self._socket.connect(self.address)
        self.connected = True
        self._read_and_parse_banner()

    def _read_and_parse_banner(self):
        banner = self._readline()
        self.cotrol_socket_element_name, self.protocol_version = banner.split('/')

    def close(self):
        if self.connected:
            # self._write_line("QUIT")
            self._socket.close()
            self.connected = False
            self._socket = None

    def engine_version(self):
        return self._read_global('version')

    def loaded_packages(self):
        packages = self._read_global('packages').strip()
        if packages:
            return packages.split('\n')
        else:
            return []

    def supported_elements(self):
        return self._read_global('classes').strip().split('\n')

    def running_config(self):
        return self._read_global('config')

    def hotswap(self, new_config):
        new_config = self._migrate_control_elements(new_config)
        self._write_global('hotconfig', data=new_config)
        for _ in xrange(CONNECT_RETRIES):
            try:
                self.close()
                self.connect(self.address, self.family)
                # try to pull the config again to make sure we are reconnected
                self.running_config()
                break
            except socket.error:
                time.sleep(0.1)

    def elements_names(self):
        raw = self._read_global('list')

        # The first line is the number of elements
        elements = raw.strip().split('\n')[1:]
        return elements

    def element_handlers(self, element_name):
        handlers = self._element_handlers_with_attributes(element_name)
        # each handler has the form (<handler_name>, <rw attributes>")
        # we need only the name
        return [name for name, attribute in handlers]

    def _element_handlers_with_attributes(self, element_name):
        handlers = self.read_handler(element_name, 'handlers').strip().split('\n')

        # each handler has the form "<handler_name> <rw attributes>"
        return [tuple(handler.strip().split('\t')) for handler in handlers]

    def element_class(self, element_name):
        return self.read_handler(element_name, 'class')

    def element_config(self, element_name):
        return self.read_handler(element_name, 'config')

    def element_ports(self, element_name):
        return self.read_handler(element_name, 'ports')

    def element_input_counts(self, element_name):
        return self.read_handler(element_name, 'icounts').strip().split('\n')

    def element_output_counts(self, element_name):
        return self.read_handler(element_name, 'ocounts').strip().split('\n')

    def is_readable_handler(self, element_name, handler_name):
        cmd = self._build_cmd(Commands.CHECK_READ, element_name, handler_name, '')
        self._write_line(cmd)
        response_code, response_msg = self._read_response()
        return response_code == ResponseCodes.OK

    def is_writeable_handler(self, element_name, handler_name):
        cmd = self._build_cmd(Commands.CHECK_WRITE, element_name, handler_name, '')
        self._write_line(cmd)
        response_code, response_msg = self._read_response()
        return response_code == ResponseCodes.OK

    def write_handler(self, element_name, handler_name, params='', data=''):
        if data:
            cmd = self._build_cmd(Commands.WRITE_DATA, element_name, handler_name, str(len(data)))
        else:
            cmd = self._build_cmd(Commands.WRITE, element_name, handler_name, params)
        self._write_line(cmd)
        if data:
            self._write_raw(data)
        response_code, response_code_msg = self._read_response()
        if response_code not in (ResponseCodes.OK, ResponseCodes.OK_BUT_WITH_WARNINGS):
            self._raise_exception(element_name, handler_name, response_code, response_code_msg)
        return response_code

    def read_handler(self, element_name, handler_name, params=''):
        cmd = self._build_cmd(Commands.READ, element_name, handler_name, params)
        self._write_line(cmd)
        response_code, response_code_msg = self._read_response()
        if response_code not in (ResponseCodes.OK, ResponseCodes.OK_BUT_WITH_WARNINGS):
            self._raise_exception(element_name, handler_name, response_code, response_code_msg)
        data_size = self._read_data_size()
        data = self._read_raw(data_size)
        return data

    def operations_sequence(self, operations, preserve_order=False):
        # Currently there is no 'smart' way in click of doing a bunch of read or write calls
        # so we just do them one after the other using the basic
        results = collections.OrderedDict()
        for operation in operations:
            operation_type = operation['type']
            element_name = operation['element_name']
            handler_name = operation['handler_name']
            params = operation.get('params', '')
            key = self._build_full_handler_name(element_name, handler_name)
            if operation_type == 'READ':
                operation_function = self.read_handler
            elif operation_type == 'WRITE':
                operation_function = self.write_handler
            else:
                operation_function = lambda en, hn, pa: UnknownHandlerOperation(
                    "Unknown operation: %s" % operation_type)
            try:
                results[key] = operation_function(element_name, handler_name, params)
            except ControlError as e:
                results[key] = e
        return results

    def _read_global(self, handler_name, params=''):
        return self.read_handler(None, handler_name, params)

    def _write_global(self, handler_name, params='', data=''):
        self.write_handler(None, handler_name, params, data)

    def _config_requirements(self):
        reqs = self._read_global('requirements').strip()
        if reqs:
            return reqs.split('\n')
        else:
            return []

    def _raise_exception(self, element_name, handler_name, response_code, response_code_msg):
        exception = _EXCPTIONS_CODE_MAPPING[response_code]
        exception_msg = self._build_read_exception_message(element_name, handler_name, response_code_msg)
        raise exception(exception_msg)

    def _build_read_exception_message(self, element_name, handler_name, response_code_msg):
        handler = self._build_full_handler_name(element_name, handler_name)
        return 'Error reading {handler}: {msg}'.format(handler=handler, msg=response_code_msg)

    def _build_cmd(self, command, element_name, handler_name, params):
        handler = self._build_full_handler_name(element_name, handler_name)
        cmd = '{cmd} {handler}'.format(cmd=command, handler=handler)
        if params:
            cmd += ' {params}'.format(params=params)
        return cmd

    def _build_full_handler_name(self, element_name, handler_name):
        if element_name:
            handler = "{element}.{handler}".format(element=element_name, handler=handler_name)
        else:
            handler = handler_name

        return handler

    def _read_response(self):
        last_line = self._readline()
        response = last_line[3:]
        while last_line[3] == '-':
            last_line = self._readline()
            response += last_line[3:]
        response_code = int(last_line[:3])
        return response_code, response

    def _read_data_size(self):
        data_size_line = self._readline()
        return int(data_size_line.split(' ')[1])

    def _read_raw(self, length):
        while len(self._buffer) < length:
            self._buffer += self._socket.recv(length - len(self._buffer))
        data, self._buffer = self._buffer[:length], self._buffer[length:]
        return data

    def _readline(self, delim='\r\n'):
        return self._read_until(delim)

    def _read_until(self, end='\r\n'):
        end_index = self._buffer.find(end)
        while end_index == -1:
            data = self._socket.recv(2048)
            self._buffer += data
            end_index = self._buffer.find(end)
        line, self._buffer = self._buffer[:end_index], self._buffer[end_index + len(end):]
        return line

    def _write_line(self, data, delim='\r\n'):
        self._write_raw("{data}{delim}".format(data=data, delim=delim))

    def _write_raw(self, data):
        total_length = len(data)
        offset = 0
        while offset < total_length:
            offset += self._socket.send(data[offset:])

    def _migrate_control_elements(self, new_config):
        old_config = self.running_config()
        old_control_socket = CONTROL_SOCKET_REGEXP.findall(old_config)
        old_chatter_socket = CHATTER_SOCKET_REGEXP.findall(old_config)
        new_control_socket = CONTROL_SOCKET_REGEXP.findall(new_config)
        new_chatter_socket = CHATTER_SOCKET_REGEXP.findall(new_config)
        if not new_chatter_socket and old_chatter_socket:
            # we add the old ChatterSocket only if it is not present in the new config but was in the old
            chatter_socket = old_chatter_socket[0] + ';\n'
            new_config = chatter_socket + new_config
        if not new_control_socket and old_control_socket:
            # we add the old ControlSocket only if it is not present in the new config but was in the old
            control_socket = old_control_socket[0] + ';\n'
            new_config = control_socket + new_config

        return new_config

if __name__ == "__main__":
    cs = ClickControlClient()
    cs.connect(("127.0.0.1", 9000))
    print("Click version: {version}".format(version=cs.engine_version()))
    print(cs.read_handler(None, 'handlers'))
    print("Packages:{packages}".format(packages=cs.loaded_packages()))
    print("Supported elements: {elements}".format(elements=cs.supported_elements()))
    print('Router config:\n{config}'.format(config=cs.running_config()))
    for element in cs.elements_names():
        s = "%s\n" % element
        for handler_name, handler_attr in cs.element_handlers(element):
            if 'r' in handler_attr and handler_name != 'handlers':
                handler_value = cs.read_handler(element, handler_name)
                s += "\t%s: %s\n" % (handler_name, repr(handler_value))
        print(s)
