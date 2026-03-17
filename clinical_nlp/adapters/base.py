from abc import ABC, abstractmethod
from clinical_nlp.schemas.input import ClinicalInput
from typing import Iterator


class DataAdapter(ABC):
    """Abstract interface for loading clinical cases.

    Implement this to plug in a new data source (MIMIC, FHIR, etc.)
    without changing the core pipeline.
    """

    @abstractmethod
    def load_cases(self, source: str) -> list[ClinicalInput]:
        """Load all cases from a source (file path, DB connection string, etc.)."""
        ...

    @abstractmethod
    def stream_cases(self, source: str) -> Iterator[ClinicalInput]:
        """Yield ClinicalInput one at a time for large datasets."""
        ...

    @abstractmethod
    def validate_schema(self, raw_record: dict) -> ClinicalInput:
        """Transform and validate a raw external record into ClinicalInput."""
        ...
