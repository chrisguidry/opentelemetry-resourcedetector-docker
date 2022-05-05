import functools
import os
import re
import socket
from contextlib import contextmanager
from typing import Generator, Optional

from opentelemetry.sdk.resources import Resource, ResourceDetector
from opentelemetry.semconv.resource import ResourceAttributes


class NotInDocker(Exception):
    pass


class DockerResourceDetector(ResourceDetector):
    """Detects OpenTelemetry Resource attributes for a container running within
    Docker, providing the `container.*` attributes if detected."""

    @functools.lru_cache(maxsize=1)
    def container_id(self) -> str:
        cgroup_pattern = r'\d+:[\w=]+:/docker(-[ce]e)?/(?P<container_id>\w+)'
        for line in self.cgroup_lines():
            if match := re.match(cgroup_pattern, line):
                return match.group('container_id')
        raise NotInDocker()

    @functools.lru_cache(maxsize=1)
    def cgroup_lines(self):  # pylint: disable=no-self-use
        with open('/proc/self/cgroup', 'r', encoding='utf-8') as cgroups:
            return list(cgroups)

    @functools.lru_cache(maxsize=1)
    def running_in_docker(self) -> bool:
        try:
            return bool(self.container_id())
        except FileNotFoundError:
            pass
        except NotInDocker:
            pass
        return False

    def detect(self) -> Resource:
        if not self.running_in_docker():
            return Resource.get_empty()

        return Resource(
            {
                ResourceAttributes.CONTAINER_RUNTIME: 'docker',
                ResourceAttributes.CONTAINER_ID: self.container_id(),
            }
        )
