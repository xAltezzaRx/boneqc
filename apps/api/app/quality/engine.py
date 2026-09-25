from app.ai.contracts import AIAnalysisResponse
from app.models.enums import AnalysisResultStatus
from app.quality.contracts import (
    QualityEvaluation,
    QualityViolation,
)

PASS_THRESHOLD = 0.80
FAIL_THRESHOLD = 0.40
QUALITY_ENGINE_VERSION = "0.1.0"


class QualityEngine:
    def evaluate(
        self,
        response: AIAnalysisResponse,
    ) -> QualityEvaluation:
        observations = response.observations

        if not observations:
            return QualityEvaluation(
                status=AnalysisResultStatus.CANNOT_ASSESS,
                quality_score=None,
                engine_version=QUALITY_ENGINE_VERSION,
                explanations=[
                    "No quality observations were produced.",
                ],
            )

        if any(
            not item.assessable or item.score is None
            for item in observations
        ):
            return QualityEvaluation(
                status=AnalysisResultStatus.CANNOT_ASSESS,
                quality_score=None,
                engine_version=QUALITY_ENGINE_VERSION,
                explanations=[
                    (
                        "At least one required quality observation "
                        "could not be assessed."
                    )
                ],
            )

        scores = [
            float(item.score)
            for item in observations
            if item.score is not None
        ]

        quality_score = round(
            sum(scores) / len(scores),
            4,
        )

        violations: list[QualityViolation] = []

        for item in observations:
            score = float(item.score)

            if score < FAIL_THRESHOLD:
                violations.append(
                    QualityViolation(
                        code=item.code,
                        severity=AnalysisResultStatus.FAIL,
                        score=score,
                        threshold=FAIL_THRESHOLD,
                        message=item.message,
                    )
                )

            elif score < PASS_THRESHOLD:
                violations.append(
                    QualityViolation(
                        code=item.code,
                        severity=AnalysisResultStatus.REVIEW,
                        score=score,
                        threshold=PASS_THRESHOLD,
                        message=item.message,
                    )
                )

        if any(
            item.severity == AnalysisResultStatus.FAIL
            for item in violations
        ):
            final_status = AnalysisResultStatus.FAIL

        elif violations:
            final_status = AnalysisResultStatus.REVIEW

        else:
            final_status = AnalysisResultStatus.PASS

        explanations = [
            (
                f"{item.code}: score={item.score:.2f}, "
                f"threshold={item.threshold:.2f}, "
                f"severity={item.severity.value}"
            )
            for item in violations
        ]

        if not explanations:
            explanations.append(
                "All assessed observations satisfy PASS thresholds."
            )

        return QualityEvaluation(
            status=final_status,
            quality_score=quality_score,
            engine_version=QUALITY_ENGINE_VERSION,
            violations=violations,
            explanations=explanations,
        )


quality_engine = QualityEngine()
