from unittest import mock

from opentelemetry.sdk.resources import Resource

from opentelemetry.resourcedetector.docker import DockerResourceDetector


def test_outside_docker():
    with mock.patch.object(DockerResourceDetector, 'running_in_docker') as m:
        m.return_value = False
        assert DockerResourceDetector().detect() == Resource.get_empty()
