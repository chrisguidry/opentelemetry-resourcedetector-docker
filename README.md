# opentelemetry-resourcedetector-docker

An OpenTelemetry package to populates Resource attributes from Docker containers.

## Usage

```
from opentelemetry.sdk.resources import get_aggregated_resources
from opentelemetry_resourcedetector_docker import DockerResourceDetector

...

resource = get_aggregated_resources([
    DockerResourceDetector(),
    SomeOtherResourceDetector()
])

... pass the returned `resource` to a TracerProvder, for example ...
```
