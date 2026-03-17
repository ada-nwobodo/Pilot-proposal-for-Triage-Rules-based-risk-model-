from .base import DataAdapter
from .synthetic import SyntheticDataAdapter

ADAPTER_REGISTRY: dict[str, type[DataAdapter]] = {
    "synthetic": SyntheticDataAdapter,
    # "mimic": MimicDataAdapter,        # add when implemented
    # "epic_fhir": EpicFHIRAdapter,     # add when implemented
}

__all__ = ["DataAdapter", "SyntheticDataAdapter", "ADAPTER_REGISTRY"]
