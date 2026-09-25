from app.ai.contracts import AIAnalysisResponse
from app.uncertainty.contracts import UncertaintyEvaluation

UNCERTAINTY_ENGINE_VERSION = "0.1.0"

REVIEW_CONFIDENCE_THRESHOLD = 0.75
CANNOT_ASSESS_CONFIDENCE_THRESHOLD = 0.50


class UncertaintyEngine:
    def evaluate(
        self,
        response: AIAnalysisResponse,
    ) -> UncertaintyEvaluation:
        observations = response.observations

        if not observations:
            return UncertaintyEvaluation(
                decision="CANNOT_ASSESS",
                engine_version=UNCERTAINTY_ENGINE_VERSION,
                reasons=[
                    "No observations were produced.",
                ],
            )

        if any(
            not observation.assessable
            for observation in observations
        ):
            return UncertaintyEvaluation(
                decision="CANNOT_ASSESS",
                engine_version=UNCERTAINTY_ENGINE_VERSION,
                reasons=[
                    (
                        "At least one required observation "
                        "was marked as not assessable."
                    )
                ],
            )

        if any(
            observation.confidence is None
            for observation in observations
        ):
            return UncertaintyEvaluation(
                decision="CANNOT_ASSESS",
                engine_version=UNCERTAINTY_ENGINE_VERSION,
                reasons=[
                    (
                        "At least one required observation "
                        "does not contain confidence."
                    )
                ],
            )

        confidences = [
            float(observation.confidence)
            for observation in observations
            if observation.confidence is not None
        ]

        minimum_confidence = min(confidences)
        mean_confidence = round(
            sum(confidences) / len(confidences),
            4,
        )

        if (
            minimum_confidence
            < CANNOT_ASSESS_CONFIDENCE_THRESHOLD
        ):
            return UncertaintyEvaluation(
                decision="CANNOT_ASSESS",
                minimum_confidence=minimum_confidence,
                mean_confidence=mean_confidence,
                engine_version=UNCERTAINTY_ENGINE_VERSION,
                reasons=[
                    (
                        "Minimum confidence is below the "
                        "cannot-assess threshold."
                    )
                ],
            )

        if minimum_confidence < REVIEW_CONFIDENCE_THRESHOLD:
            return UncertaintyEvaluation(
                decision="REVIEW",
                minimum_confidence=minimum_confidence,
                mean_confidence=mean_confidence,
                engine_version=UNCERTAINTY_ENGINE_VERSION,
                reasons=[
                    (
                        "Minimum confidence is below the "
                        "automatic-accept threshold."
                    )
                ],
            )

        return UncertaintyEvaluation(
            decision="ACCEPT",
            minimum_confidence=minimum_confidence,
            mean_confidence=mean_confidence,
            engine_version=UNCERTAINTY_ENGINE_VERSION,
            reasons=[
                (
                    "All required observations satisfy "
                    "the confidence threshold."
                )
            ],
        )


uncertainty_engine = UncertaintyEngine()
