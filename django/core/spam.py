"""Classify submissions using the configured primary and fallback decision models."""

import logging
import time
from dataclasses import dataclass

import requests
from django.conf import settings

from .models import SpamDetectionSettings

logger = logging.getLogger(__name__)

SPAM_QUESTION = {
    "instructions": (
        "This content was submitted to CoMSES.Net, a community site for computational modeling in the social and "
        "ecological sciences. Members publish agent-based and other computational models (codebases), post jobs "
        "and events related to research, modeling, and simulation, and keep public member profiles. Submissions "
        "come from researchers worldwide, are often brief or written in imperfect English, and may be tests or "
        "drafts. Is this submission spam?"
    ),
    "criteria": {
        "true": (
            "Promotes a product, service, website, or business unrelated to research or modeling; SEO or link spam; "
            "scams; adult content; or academic services such as paid essay writing, even when phrased in research "
            "language"
        ),
        "false": (
            "A genuine model, research job, academic event, or member profile, or an honest test, draft, or "
            "low-effort post, however brief, informal, or poorly written"
        ),
    },
}


class CloudflareDecisionModel:
    """
    Cloudflare Workers AI decision models.
    https://developers.cloudflare.com/workers-ai/models/clef-omni/
    """

    provider = "cloudflare"
    timeout = 30

    def __init__(self, model: str):
        self.model = model
        self.url = (
            f"https://api.cloudflare.com/client/v4/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}"
            f"/ai/run/@cf/cloudflare/{model}"
        )

    @staticmethod
    def is_configured() -> bool:
        return bool(settings.CLOUDFLARE_ACCOUNT_ID and settings.CLOUDFLARE_AI_API_TOKEN)

    def spam_probability(self, content: dict, timeout: float) -> float:
        payload = {
            "model": self.model,
            "state": content,
            "questions": {"spam": {"type": "noul", **SPAM_QUESTION}},
        }
        response = requests.post(
            self.url,
            headers={"Authorization": f"Bearer {settings.CLOUDFLARE_AI_API_TOKEN}"},
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["result"]["answers"]["spam"]["noul"]


class AsuDecisionModel:
    """
    ASU Research Computing Verdicts API.
    https://docs.rc.asu.edu/ai/api/verdicts/
    """

    provider = "asu"
    timeout = 300

    def __init__(self, model: str):
        self.model = model
        self.url = f"{settings.VOYAGER_AI_BASE_URL.rstrip('/')}/verdicts"

    @staticmethod
    def is_configured() -> bool:
        return bool(settings.VOYAGER_AI_API_KEY)

    def spam_probability(self, content: dict, timeout: float) -> float:
        payload = {
            "model": self.model,
            "state": content,
            "questions": {"spam": {"type": "boolean", **SPAM_QUESTION}},
        }
        response = requests.post(
            self.url,
            headers={"Authorization": f"Bearer {settings.VOYAGER_AI_API_KEY}"},
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["verdicts"]["spam"]["probabilities"]["true"]


PROVIDERS = {
    SpamDetectionSettings.Provider.CLOUDFLARE: CloudflareDecisionModel,
    SpamDetectionSettings.Provider.ASU: AsuDecisionModel,
}


class SpamDetectionUnavailable(Exception):
    """
    Neither the primary nor the fallback model has an API key deployed
    """


@dataclass
class SpamCheck:
    is_spam: bool
    detection_method: str
    detection_details: dict


def configured_models(config: SpamDetectionSettings) -> list[tuple]:
    """
    The primary then fallback model with their thresholds, skipping any without an API key
    """
    slots = [
        (config.primary_provider, config.primary_model, config.primary_threshold),
        (config.fallback_provider, config.fallback_model, config.fallback_threshold),
    ]
    models = []
    for provider, model, threshold in slots:
        if not provider or not model:
            continue
        adapter = PROVIDERS[provider]
        if adapter.is_configured():
            models.append((adapter(model), threshold))
    return models


def detect_spam(config: SpamDetectionSettings, content: dict) -> SpamCheck:
    """
    Ask the primary model whether content is spam, falling back to the other model if it fails or is slow. Raises
    if the last model fails, so the caller can retry
    """
    models = configured_models(config)
    if not models:
        raise SpamDetectionUnavailable("no spam detection model has an API key")
    fallback_from = []
    for index, (decision_model, threshold) in enumerate(models):
        is_last = index == len(models) - 1
        name = f"{decision_model.provider}/{decision_model.model}"
        started = time.monotonic()
        try:
            timeout = decision_model.timeout if is_last else config.primary_timeout
            spam_probability = decision_model.spam_probability(content, timeout)
            if type(spam_probability) not in (int, float) or not 0 <= spam_probability <= 1:
                raise ValueError("Spam probability must be a number between 0 and 1")
        except (requests.RequestException, KeyError, TypeError, ValueError) as error:
            if is_last:
                raise
            logger.warning("spam detection with %s failed, falling back: %s", name, error)
            fallback_from.append({"model": name, "error": str(error)[:500]})
            continue
        details = {
            "spam_probability": spam_probability,
            "threshold": threshold,
            "latency_ms": round((time.monotonic() - started) * 1000),
            # what the model saw, for review and for building eval datasets
            "input": content,
        }
        if fallback_from:
            details["fallback_from"] = fallback_from
        return SpamCheck(is_spam=spam_probability >= threshold, detection_method=name, detection_details=details)
