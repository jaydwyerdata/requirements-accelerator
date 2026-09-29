"""The field ledger: one record per field, tagged with how it was learned.

Implements the provenance model from docs/provenance-model.md: every field carries a state
(stated, inferred, assumed or missing) and a stronger state always overwrites a weaker one,
never the reverse. Precedence: stated > inferred > assumed > missing.

Implements the ownership rule from docs/readiness-scoring.md: most fields default to the
requester, a short explicit list belongs to the team instead.
"""

from dataclasses import dataclass
from enum import Enum


class ProvenanceState(Enum):
    STATED = 3
    INFERRED = 2
    ASSUMED = 1
    MISSING = 0


class Owner(Enum):
    REQUESTER = "requester"
    TEAM = "team"


# From docs/readiness-scoring.md: the only fields a data engineer can close by examining
# source systems or governance metadata, without needing the requester's intent.
TEAM_OWNED_FIELDS = frozenset({
    "source_systems",
    "fan_out_risk",
    "cardinality_risk",
    "volume",
    "growth_rate",
})


def owner_for(field_id: str) -> Owner:
    return Owner.TEAM if field_id in TEAM_OWNED_FIELDS else Owner.REQUESTER


@dataclass
class FieldRecord:
    field_id: str
    layer: str
    value: object
    state: ProvenanceState
    source: str
    owner: Owner
    note: str = ""


class Ledger:
    """One row per field. Setting a field never downgrades an existing stronger state."""

    def __init__(self):
        self._records: dict[str, FieldRecord] = {}

    def set(self, field_id: str, layer: str, value: object, state: ProvenanceState,
            source: str, note: str = "") -> None:
        existing = self._records.get(field_id)
        if existing is not None and existing.state.value > state.value:
            return
        self._records[field_id] = FieldRecord(
            field_id=field_id,
            layer=layer,
            value=value,
            state=state,
            source=source,
            owner=owner_for(field_id),
            note=note,
        )

    def get(self, field_id: str) -> FieldRecord | None:
        return self._records.get(field_id)

    def all(self) -> list[FieldRecord]:
        return list(self._records.values())

    def is_missing(self, field_id: str) -> bool:
        record = self._records.get(field_id)
        return record is None or record.state == ProvenanceState.MISSING

    def known_values(self) -> dict[str, object]:
        """field_id to value for everything not missing, for grounding a reasoner call
        (a reframe, a term consolidation) in what the requester has actually said so far,
        rather than the field's technical name or an invented example."""
        return {
            field_id: record.value
            for field_id, record in self._records.items()
            if record.state != ProvenanceState.MISSING
        }
