# SYNTHETIC DATA generator for PartFlow.
# Produces a coherent, referentially-intact multi-month supply-chain dataset.
# See docs/adr/0001-supply-chain-source-data-model.md for the model and rationale.

from .config import GenConfig

__all__ = ["GenConfig"]
