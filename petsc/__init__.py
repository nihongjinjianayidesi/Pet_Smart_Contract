"""
PetSC 链下业务层（Python）。

本包当前提供证据存证与哈希校验通用能力（EvidenceService）。
"""

from .evidence_service import EvidenceService
from .fabric_client import InMemoryFabricStub, FabricClient
from .pricing_engine import PricingEngine
from .contract_orchestrator import ContractOrchestrator
from .compensation_engine import CompensationEngine, PaymentSimulator

__all__ = ["EvidenceService", "FabricClient", "InMemoryFabricStub", "PricingEngine", "ContractOrchestrator", "CompensationEngine", "PaymentSimulator"]
