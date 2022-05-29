from unittest import mock

import pytest
from opentelemetry.sdk.resources import Resource

from opentelemetry_resourcedetector_docker import DockerResourceDetector, NotInDocker


@pytest.fixture
def docker_mountinfo():
    cgroup_lines = [
        '3668 3663 0:94 / /dev/shm rw,nosuid,nodev,noexec,relatime - tmpfs shm rw,size=65536k,inode64'  # noqa: E501
        '3669 3661 259:2 /var/lib/docker/containers/c2c89fc760c453b930a798f451792d96b5736be7686f25ef/resolv.conf /etc/resolv.conf rw,relatime - ext4 /dev/nvme0n1p2 rw,errors=remount-ro'  # noqa: E501
        '3670 3661 259:2 /var/lib/docker/containers/c2c89fc760c453b930a798f451792d96b5736be7686f25ef/hostname /etc/hostname rw,relatime - ext4 /dev/nvme0n1p2 rw,errors=remount-ro'  # noqa: E501
        '3671 3661 259:2 /var/lib/docker/containers/c2c89fc760c453b930a798f451792d96b5736be7686f25ef/hosts /etc/hosts rw,relatime - ext4 /dev/nvme0n1p2 rw,errors=remount-ro'  # noqa: E501
        '3543 3663 0:92 /0 /dev/console rw,nosuid,noexec,relatime - devpts devpts rw,gid=5,mode=620,ptmxmode=666'  # noqa: E501
    ]
    opened = mock.mock_open(read_data='\n'.join(cgroup_lines))
    with mock.patch('builtins.open', opened) as mock_file:
        yield mock_file


def test_cgroup_v2_container_id(docker_mountinfo):
    assert DockerResourceDetector().running_in_docker()

    assert (
        DockerResourceDetector().container_id()
        == 'c2c89fc760c453b930a798f451792d96b5736be7686f25ef'
    )


def test_cgroup_v2_resource_includes_container_id(docker_mountinfo):
    assert DockerResourceDetector().running_in_docker()

    assert DockerResourceDetector().detect().attributes == {
        'container.runtime': 'docker',
        'container.id': 'c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
    }


@pytest.fixture
def docker_cgroups():
    cgroup_lines = [
        '12:devices:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
        '11:memory:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
        '10:net_cls:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
        '9:pids:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
        '8:cpuset:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
        '7:rdma:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
        '6:cpu,cpuacct:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
        '5:hugetlb:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
        '4:freezer:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
        '3:blkio:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
        '2:perf_event:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
        '1:name=systemd:/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
        '0::/docker/c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
    ]
    opened = mock.mock_open(read_data='\n'.join(cgroup_lines))
    with mock.patch('builtins.open', opened) as mock_file:
        yield mock_file


def test_cgroup_v1_container_id(docker_cgroups):
    assert DockerResourceDetector().running_in_docker()

    assert (
        DockerResourceDetector().container_id()
        == 'c2c89fc760c453b930a798f451792d96b5736be7686f25ef'
    )


def test_cgroup_v1_resource_includes_container_id(docker_cgroups):
    assert DockerResourceDetector().running_in_docker()

    assert DockerResourceDetector().detect().attributes == {
        'container.runtime': 'docker',
        'container.id': 'c2c89fc760c453b930a798f451792d96b5736be7686f25ef',
    }


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

    assert DockerResourceDetector().detect() == Resource.get_empty()


@pytest.fixture
def not_even_a_cgroup_file():
    with mock.patch('builtins.open', side_effect=FileNotFoundError):
        yield


def test_not_even_in_a_cgroup(not_even_a_cgroup_file):
    assert not DockerResourceDetector().running_in_docker()

    with pytest.raises(FileNotFoundError):
        DockerResourceDetector().container_id()

    assert DockerResourceDetector().detect() == Resource.get_empty()
