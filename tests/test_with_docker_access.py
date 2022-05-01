import os
from typing import Dict, Generator
from unittest import mock

import pytest
from docker import DockerClient
from docker.models.containers import Container
from docker.models.images import Image
from opentelemetry.sdk.resources import Resource

from opentelemetry.resourcedetector.docker import DockerResourceDetector


@pytest.fixture
def docker_client() -> DockerClient:
    with mock.patch.object(DockerResourceDetector, 'running_in_docker') as m:
        m.return_value = True

        with mock.patch('docker.from_env', autospec=True) as from_env:
            from_env.return_value = mock.Mock(spec=DockerClient)
            yield from_env.return_value


@pytest.fixture
def container_id():
    with mock.patch.object(DockerResourceDetector, 'container_id') as m:
        m.return_value = 'the-container-id'
        yield m.return_value


@pytest.fixture
def container(docker_client: DockerClient, container_id: str):
    docker_client.containers.get.return_value = mock.Mock(
        spec=Container,
        id=container_id,
        image=mock.Mock(
            spec=Image,
            id='the-image-id',
            tags=['python:3.10', 'another:one'],
        ),
    )
    docker_client.containers.get.return_value.name = 'example-container'
    yield docker_client.containers.get.return_value


@pytest.fixture
def resource(container) -> Dict:
    resource = DockerResourceDetector().detect()
    assert resource != Resource.get_empty()
    return dict(resource.attributes)


def test_container_runtime(resource: Dict):
    assert resource['container.runtime'] == 'docker'


def test_container_id(resource: Dict):
    assert resource['container.id'] == 'the-container-id'


def test_container_name(resource: Dict):
    assert resource['container.name'] == 'example-container'


def test_container_image_name(resource: Dict):
    assert resource['container.image.name'] == 'python'


def test_container_image_tag(resource: Dict):
    assert resource['container.image.tag'] == '3.10'


@pytest.fixture
def container_with_untagged_image(container):
    container.image.tags = []
    return container


def test_only_image_id(container_with_untagged_image, resource: Dict):
    assert resource['container.image.name'] == 'the-image-id'
    assert resource['container.image.tag'] == ''
