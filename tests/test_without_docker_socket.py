from typing import Dict
from unittest import mock

import pytest
from opentelemetry.sdk.resources import Resource

from opentelemetry_resourcedetector_docker import DockerResourceDetector


@pytest.fixture
def docker_client():
    with mock.patch.object(DockerResourceDetector, 'running_in_docker') as m:
        m.return_value = True

        with mock.patch('docker.from_env', autospec=True) as from_env:
            from_env.side_effect = Exception('no docker for you')
            yield


@pytest.fixture
def container_id():
    with mock.patch.object(DockerResourceDetector, 'container_id') as m:
        m.return_value = 'the-container-id'
        yield m.return_value


@pytest.fixture
def resource(docker_client, container_id) -> Dict:
    resource = DockerResourceDetector().detect()
    assert resource != Resource.get_empty()
    return dict(resource.attributes)


def test_container_runtime(resource: Dict):
    assert resource['container.runtime'] == 'docker'


def test_container_id(resource: Dict):
    assert resource['container.id'] == 'the-container-id'


def test_container_name(resource: Dict):
    assert 'container.name' not in resource


def test_container_image_name(resource: Dict):
    assert 'container.image.name' not in resource


def test_container_image_tag(resource: Dict):
    assert 'container.image.tag' not in resource
