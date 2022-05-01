import functools
import os
import re
import socket
from typing import Optional

import docker
from docker import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container
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

    @functools.lru_cache(maxsize=1)
    def docker_client(self) -> Optional[DockerClient]:
        if not self.running_in_docker():
            return None

        try:
            return docker.from_env()
        except Exception:  # pylint: disable=broad-except
            pass

        return None

    def detect(self) -> Resource:
        if not self.running_in_docker():
            return Resource.get_empty()

        container: Optional[Container] = None
        if client := self.docker_client():
            try:
                container = client.containers.get(self.container_id())
            except NotFound:
                pass

        if not container:
            return Resource(
                {
                    ResourceAttributes.CONTAINER_RUNTIME: 'docker',
                    ResourceAttributes.CONTAINER_ID: self.container_id(),
                }
            )

        try:
            image_name, image_tag = container.image.tags[0].split(':')
        except IndexError:
            image_name, image_tag = container.image.id, ''

        return Resource(
            {
                ResourceAttributes.CONTAINER_RUNTIME: 'docker',
                ResourceAttributes.CONTAINER_ID: container.id,
                ResourceAttributes.CONTAINER_NAME: container.name,
                ResourceAttributes.CONTAINER_IMAGE_NAME: image_name,
                ResourceAttributes.CONTAINER_IMAGE_TAG: image_tag,
            }
        )
