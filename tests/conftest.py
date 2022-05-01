import json
import os
import tarfile
import tempfile
from textwrap import dedent
from typing import Dict, Generator

import docker
import pytest
from docker.models.containers import Container


@pytest.fixture(scope='session')
def docker_client() -> docker.DockerClient:
    try:
        return docker.from_env()
    except Exception:  # pylint: disable=broad-except
        pass
    raise pytest.skip('Docker is not available')


@pytest.fixture(scope='session')
def example_script() -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile() as script_file:
        script_file.write(
            dedent(
                """
            import json
            from opentelemetry.resourcedetector.docker import DockerResourceDetector

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
def resource(container: Container, example_script: str) -> Dict:
    with open(example_script, mode='rb') as f:
        container.put_archive('/tmp/', f)

    result = container.exec_run("python /tmp/example.py", stdout=True, stderr=True)
    assert result.exit_code == 0, result.output

    resource_attributes = json.loads(result.output.decode())
    return resource_attributes
