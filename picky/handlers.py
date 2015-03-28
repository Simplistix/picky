from distutils.spawn import find_executable
from logging import getLogger
import os
from subprocess import check_output
from tempfile import TemporaryFile
from picky.requirements import Requirements

logger = getLogger(__name__)


class Handler(object):

    args = ()
    name = None

    @staticmethod
    def parse_line(line):
        raise NotImplementedError

    @staticmethod
    def serialise_line(name, version):
        raise NotImplementedError

    def read_source(self, if_, callable_, param, source):
        if if_:
            text = callable_(param)
            logger.info('Using %r for %s', param, self.name)
        else:
            text = ''
            logger.debug('%r not found', param)
        return self.requirements(text, source)

    def run_command(self, command):
        return check_output((command, )+self.args,
                            stderr=TemporaryFile())

    def read_file(self, path):
        with open(path) as source:
            return source.read()

    def find_executable(self, command):
        executable = find_executable(command)
        if executable:
            return True, os.path.abspath(executable)
        else:
            return False, command

    def __init__(self, command, path):
        self.executable_found, executable = self.find_executable(command)
        path_exists = os.path.exists(path)

        self.used = self.read_source(
            if_=self.executable_found,
            callable_=self.run_command,
            param=executable,
            source=' '.join((self.name, )+self.args)
        )

        self.specified = self.read_source(
            if_=path_exists,
            callable_=self.read_file,
            param=path,
            source=os.path.split(path)[-1]
        )

        if path_exists and not self.executable_found:
            logger.error('%r found but %s missing', path, self.name)

    def requirements(self, text, source):
        return Requirements(text,
                            self.parse_line,
                            self.serialise_line,
                            source)


class PipHandler(Handler):

    name = 'pip'
    args = ('freeze', )

    @staticmethod
    def parse_line(line):
        line = line.split('#')[0]
        if '==' in line:
            return (p.strip() for p in line.split('=='))

    @staticmethod
    def serialise_line(name, version):
        return name + '==' + version


class CondaHandler(Handler):

    name = 'conda'
    args = ('list', '-e')

    @staticmethod
    def parse_line(line):
        line = line.split('#')[0]
        parts = [p.strip() for p in line.split('=')]
        if len(parts) > 1:
            return parts[:2]

    @staticmethod
    def serialise_line(name, version):
        return name + '=' + version