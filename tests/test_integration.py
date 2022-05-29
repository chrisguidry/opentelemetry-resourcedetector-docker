import json
import os
import tarfile
import tempfile
import warnings
from textwrap import dedent
from typing import Dict

import pytest

with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    import docker

from docker import DockerClient
from docker.models.containers import Container


@pytest.fixture(scope='module')
def docker_client() -> DockerClient:
    if 'RUNNING_IN_GITHUB_ACTIONS' in os.environ:
        raise pytest.skip('Running in Github Actions')

    client = None
    try:
        client = docker.from_env()
        client.containers.list()
    except Exception:  # pragma: no cover
        pass

    if not client:
        raise pytest.skip('Docker is not available')  # pragma: no cover

    try:
        yield client
    finally:
        client.close()


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


@pytest.fixture(scope='session')
def example_script():
    with tempfile.NamedTemporaryFile() as script_file:
        script_file.write(
            dedent(
                """
            import json
            from opentelemetry_resourcedetector_docker import DockerResourceDetector

            detector = DockerResourceDetector()
            resource = detector.detect()
            attributes = dict(resource.attributes)

            print(json.dumps(attributes))
            """
            ).encode('utf-8')
        )
        script_file.flush()
        with tempfile.NamedTemporaryFile() as script_tar:
            with tarfile.open(script_tar.name, 'w') as tar:
                tar.add(script_file.name, 'example.py')
            yield script_tar.name


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
