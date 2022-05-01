import json
import os
import tarfile
import tempfile
from textwrap import dedent
from typing import Dict

import docker
import pytest
from docker import DockerClient
from docker.models.containers import Container


@pytest.fixture(scope='session')
def docker_client() -> DockerClient:
    try:
        client = docker.from_env()
        client.containers.list()
        return client
    except Exception:  # pragma: no cover pylint: disable=broad-except
        pass
    raise pytest.skip('Docker is not available')  # pragma: no cover


@pytest.fixture(scope='session')
def example_script():
    with tempfile.NamedTemporaryFile() as script_file:
        script_file.write(
            dedent(
                """
            import json
            from opentelemetry_resourcedetector_docker import DockerResourceDetector

            resource = DockerResourceDetector().detect()
            print(json.dumps(dict(resource.attributes)))
            """
            ).encode('utf-8')
        )
        script_file.flush()
        with tempfile.NamedTemporaryFile() as script_tar:
            with tarfile.open(script_tar.name, 'w') as tar:
                tar.add(script_file.name, 'example.py')
            yield script_tar.name


@pytest.fixture(scope='module')
def container_name(testrun_uid, worker_id) -> str:
    return f'unit-tests-{testrun_uid}-{worker_id}'


@pytest.fixture(scope='module')
def container(docker_client: DockerClient, container_name: str):
    container: Container = docker_client.containers.run(
        image='python:3.10',
        command='sleep 120s',
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


@pytest.fixture(scope='module')
def resource(container: Container, example_script: str) -> Dict:
    with open(example_script, mode='rb') as f:
        container.put_archive('/tmp/', f)

    result = container.exec_run("python /tmp/example.py", stdout=True, stderr=True)
    assert result.exit_code == 0, result.output

    resource_attributes = json.loads(result.output.decode())
    return resource_attributes


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
