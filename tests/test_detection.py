from unittest import mock

import pytest

from opentelemetry_resourcedetector_docker import DockerResourceDetector, NotInDocker


@pytest.fixture
def docker_cgroups():
    cgroup_lines = [
        '12:devices:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
        '11:memory:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
        '10:net_cls:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
        '9:pids:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
        '8:cpuset:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
        '7:rdma:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
        '6:cpu,cpuacct:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
        '5:hugetlb:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
        '4:freezer:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
        '3:blkio:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
        '2:perf_event:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
        '1:name=systemd:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
        '0::/docker/c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206',
    ]
    opened = mock.mock_open(read_data='\n'.join(cgroup_lines))
    with mock.patch('builtins.open', opened) as mock_file:
        yield mock_file


def test_container_id(docker_cgroups):
    assert DockerResourceDetector().running_in_docker()

    assert (
        DockerResourceDetector().container_id()
        == 'c2c89fc760c453b930a798f451792d96b5736be7686f257c43c8e2f622b6d206'
    )


def test_docker_client(docker_cgroups):
    with mock.patch('docker.from_env') as from_env:
        assert DockerResourceDetector().docker_client() == from_env.return_value


@pytest.fixture
def out_of_docker_cgroups():
    cgroup_lines = [
        '12:devices:/user.slice',
        '11:memory:/user.slice/user-1000.slice/user@1000.service',
        '10:net_cls,net_prio:/',
        '9:pids:/user.slice/user-1000.slice/user@1000.service',
        '8:cpuset:/',
        '7:rdma:/',
        '6:cpu,cpuacct:/user.slice',
        '5:hugetlb:/',
        '4:freezer:/',
        '3:blkio:/user.slice',
        '2:perf_event:/',
        '1:name=systemd:/user.slice/blah-blah-blah',
        '0::/user.slice/user-1000.slice/blah-blah-blah',
    ]
    opened = mock.mock_open(read_data='\n'.join(cgroup_lines))
    with mock.patch('builtins.open', opened):
        yield


def test_not_in_docker(out_of_docker_cgroups):
    assert not DockerResourceDetector().running_in_docker()

    with pytest.raises(NotInDocker):
        DockerResourceDetector().container_id()


def test_no_docker_client(out_of_docker_cgroups):
    assert not DockerResourceDetector().docker_client()


@pytest.fixture
def not_even_a_cgroup_file():
    with mock.patch('builtins.open', side_effect=FileNotFoundError):
        yield


def test_not_even_in_a_cgroup(not_even_a_cgroup_file):
    assert not DockerResourceDetector().running_in_docker()

    with pytest.raises(FileNotFoundError):
        DockerResourceDetector().container_id()


def test_definition_no_docker_client(not_even_a_cgroup_file):
    assert not DockerResourceDetector().docker_client()
