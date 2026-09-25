from app.models.enums import AnalysisResultStatus
from app.quality.contracts import QualityEvaluation
from app.uncertainty.contracts import UncertaintyEvaluation
from app.decision.contracts import FinalDecision

DECISION_RESOLVER_VERSION = "0.1.0"


class FinalDecisionResolver:
    def resolve(
        self,
        *,
        quality: QualityEvaluation,
        uncertainty: UncertaintyEvaluation,
    ) -> FinalDecision:
        if quality.status == AnalysisResultStatus.CANNOT_ASSESS:
            return FinalDecision(
                status=AnalysisResultStatus.CANNOT_ASSESS,
                resolver_version=DECISION_RESOLVER_VERSION,
                reasons=[
                    "Quality Engine could not assess the study.",
                ],
            )

        if uncertainty.decision == "CANNOT_ASSESS":
            return FinalDecision(
                status=AnalysisResultStatus.CANNOT_ASSESS,
                resolver_version=DECISION_RESOLVER_VERSION,
                reasons=[
                    (
                        "Uncertainty Engine determined that "
                        "confidence is insufficient for a QC decision."
                    )
                ],
            )

        if uncertainty.decision == "REVIEW":
            return FinalDecision(
                status=AnalysisResultStatus.REVIEW,
                resolver_version=DECISION_RESOLVER_VERSION,
                reasons=[
                    (
                        "Model confidence requires manual review "
                        "before accepting the QC decision."
                    )
                ],
            )

        return FinalDecision(
            status=quality.status,
            resolver_version=DECISION_RESOLVER_VERSION,
            reasons=[
                (
                    "Uncertainty Engine accepted the confidence level; "
                    "Quality Engine decision is preserved."
                )
            ],
        )


decision_resolver = FinalDecisionResolver()
