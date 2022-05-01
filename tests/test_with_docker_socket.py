import os
from typing import Dict, Generator

import docker
import pytest
from docker.models.containers import Container


@pytest.fixture(scope='module')
def container_name(testrun_uid) -> str:
    return f'unit-tests-with-docker-{testrun_uid}'


@pytest.fixture(scope='module')
def container(
    docker_client: docker.APIClient, container_name: str
) -> Generator[Container, None, None]:
    container: Container = docker_client.containers.run(
        image='python:3.10',
        command='sleep 60s',
        name=container_name,
        volumes={
            os.getcwd(): {'bind': '/app/', 'mode': 'rw'},
            '/var/run/docker.sock': {'bind': '/var/run/docker.sock', 'mode': 'rw'},
        },
        working_dir='/app/',
        auto_remove=True,
        detach=True,
    )

    result = container.exec_run("pip install -e .", stdout=True, stderr=True)
    assert result.exit_code == 0, result.output

    try:
        yield container
    finally:
        container.remove(force=True)


def test_container_runtime(container: Container, resource: Dict):
    assert resource['container.runtime'] == 'docker'


def test_container_id(container: Container, resource: Dict):
    assert resource['container.id'] == container.id


def test_container_name(container: Container, resource: Dict, container_name: str):
    assert resource['container.name'] == container_name


def test_container_image_name(container: Container, resource: Dict):
    assert resource['container.image.name'] == 'python'


def test_container_image_tag(container: Container, resource: Dict):
    assert resource['container.image.tag'] == '3.10'
