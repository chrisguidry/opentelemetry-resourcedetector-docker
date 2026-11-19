# opentelemetry-resourcedetector-docker

An OpenTelemetry package to populate Resource attributes from Docker containers.

## Usage

```
from opentelemetry.sdk.resources import get_aggregated_resources
from opentelemetry_resourcedetector_docker import DockerResourceDetector

...

resource = get_aggregated_resources([
    DockerResourceDetector(),
    SomeOtherResourceDetector()
])

... pass the returned `resource` to a TracerProvider, for example ...
```
