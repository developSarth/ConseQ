"""Intent parser for ECHO software failure simulations.

Extracts structured simulation intent (type, target entity, version, action)
from user natural language prompts using Gemini 2.5/3.x Flash, with a
deterministic fallback rule-engine for offline/resilient execution.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.schemas.simulation import SimulationType

log = logging.getLogger("app.agent.parser")


class ParsedIntent(BaseModel):
    simulation_type: SimulationType
    target_name: str
    target_version: str | None = None
    action: str = "SIMULATE"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: str = ""


_SYSTEM_PROMPT = """You are the AI intent classification agent for ECHO (Enterprise Software Failure Simulator).
Your task is to analyze user questions about software architectures and categorize them into:
1. "failure" - simulating an outage, service crash, network partition, or component failure.
2. "upgrade" - analyzing the change impact of updating a shared library, SDK, or dependency.
3. "recovery" - finding fallback providers, degraded modes, circuit breakers, or failover options.

The software architecture consists of these known components:
- Microservices:
  * "api-gateway" (handles API ingress, API keys, public route dispatching)
  * "auth-service" (user authentication, login sessions, credential verification)
  * "user-service" (user account profiles and data)
  * "cart-service" (shopping cart persistence)
  * "checkout-service" (checkout pipeline orchestration)
  * "payment-service" (payment authorization and processing)
  * "order-service" (order management and transactions)
  * "inventory-service" (stock and warehouse catalog)
  * "fraud-detection-service" (transaction risk analysis)
  * "catalog-service" (product listings and details)
  * "search-service" (product search engine)
  * "shipping-service" (carrier logistics and shipping rates)
  * "notification-service" (customer email and SMS alerts)
  * "recommendation-service" (product recommendations)
- Datastores & Caches:
  * "cache_redis_session" (Session Redis Cluster)
  * "db_auth_pg" (Auth PostgreSQL)
  * "db_order_pg" (Orders PostgreSQL)
  * "db_inventory_pg" (Inventory PostgreSQL)
  * "db_catalog_mongo" (Catalog MongoDB)
  * "queue_order_kafka" (Order Kafka Event Stream)
- Third-Party SaaS Providers:
  * "tp_stripe" (Stripe Payments Gateway)
  * "tp_paypal" (PayPal Backup Gateway)
  * "tp_twilio" (Twilio SMS Provider)
  * "tp_sendgrid" (SendGrid Email Provider)
  * "tp_datadog" (Datadog APM & Telemetry)
- Shared Libraries:
  * "crypto-jwt"
  * "fintech-payment-sdk"
  * "grpc-common-proto"
  * "structured-logger"

CRITICAL INSTRUCTIONS FOR TARGET RESOLUTION:
- You MUST choose the single best matching component name from the list above for "target_name".
- If the user mentions "API key", "API keys", "API key fault", "ingress", "gateway", or "routing", map target_name to "api-gateway".
- If the user mentions "authentication", "login", or "token validation", map target_name to "auth-service".
- If the user mentions "credit card", "payment", or "Stripe", map target_name to "payment-service" or "tp_stripe".
- If the user mentions "Redis", "session", or "cache", map target_name to "cache_redis_session".
- If the user mentions "PostgreSQL" or "Orders DB", map target_name to "db_order_pg".
- If the user mentions "Kafka" or "event stream", map target_name to "queue_order_kafka".

Return ONLY a JSON object with this exact schema:
{
  "simulation_type": "failure" | "upgrade" | "recovery",
  "target_name": "<exact component name from the list above, e.g. 'api-gateway', 'auth-service', 'tp_stripe', 'crypto-jwt'>",
  "target_version": "<target version string if mentioned, e.g. '3.0.0', or null>",
  "action": "<brief description of the action, e.g. 'OUTAGE', 'UPGRADE', 'FAILOVER'>",
  "reasoning": "<brief 1-sentence reason>"
}
"""


def _rule_based_fallback(prompt: str) -> ParsedIntent:
    """Deterministic extractor when LLM is offline or unconfigured."""
    text = prompt.lower()

    # 1. Recovery questions
    if any(k in text for k in ("fallback", "keep checkout working", "payment provider fails", "recovery", "failover", "degraded")):
        # Target extraction
        target = "stripe"
        if "stripe" in text or "payment" in text or "provider" in text:
            target = "tp_stripe"
        elif "twilio" in text or "sms" in text:
            target = "tp_twilio"
        elif "checkout" in text:
            target = "svc_checkout"
        return ParsedIntent(
            simulation_type=SimulationType.RECOVERY,
            target_name=target,
            action="FAILOVER_ANALYSIS",
            confidence=0.85,
            reasoning="Detected recovery / fallback keywords in prompt.",
        )

    # 2. Upgrade / change impact questions
    if any(k in text for k in ("upgrade", "update", "library", "version", "bump", "deprecat")):
        # Extract version number if present (e.g. "version 3", "v3", "3.0")
        ver_match = re.search(r'(?:version|v)\s*([0-9]+(?:\.[0-9]+)*)', text)
        target_ver = f"{ver_match.group(1)}.0.0" if ver_match else "3.0.0"

        # Extract library name
        target = "crypto-jwt"
        if "jwt" in text or "crypto" in text:
            target = "crypto-jwt"
        elif "payment" in text or "sdk" in text:
            target = "fintech-payment-sdk"
        elif "grpc" in text:
            target = "grpc-common-proto"
        elif "logger" in text or "log" in text:
            target = "structured-logger"

        return ParsedIntent(
            simulation_type=SimulationType.UPGRADE,
            target_name=target,
            target_version=target_ver,
            action="UPGRADE_IMPACT",
            confidence=0.88,
            reasoning="Detected library upgrade keywords in prompt.",
        )

    # 3. Default to failure simulation
    # Match specific multi-word infrastructure first
    if "api-gateway" in text or "api gateway" in text or "api key" in text or "api-key" in text or "apikey" in text or "ingress" in text:
        target = "svc_gateway"
    elif "fraud" in text:
        target = "svc_fraud"
    elif "inventory" in text and ("db" in text or "postgres" in text or "database" in text or "deadlock" in text):
        target = "db_inventory_pg"
    elif "inventory" in text:
        target = "svc_inventory"
    elif ("order" in text or "orders" in text) and ("db" in text or "postgres" in text or "database" in text or "crash" in text):
        target = "db_order_pg"
    elif "order" in text or "orders" in text:
        target = "svc_order"
    elif "auth" in text and ("db" in text or "postgres" in text or "database" in text):
        target = "db_auth_pg"
    elif "auth" in text or "authentication" in text or "login" in text:
        target = "svc_auth"
    elif "cart" in text and ("cache" in text or "redis" in text):
        target = "cache_redis_session"
    elif "cart" in text:
        target = "svc_cart"
    elif "checkout" in text:
        target = "svc_checkout"
    elif "payment" in text or "payments" in text:
        if "stripe" in text:
            target = "tp_stripe"
        elif "paypal" in text:
            target = "tp_paypal"
        else:
            target = "svc_payment"
    elif "stripe" in text:
        target = "tp_stripe"
    elif "paypal" in text:
        target = "tp_paypal"
    elif "twilio" in text:
        target = "tp_twilio"
    elif "sendgrid" in text:
        target = "tp_sendgrid"
    elif "datadog" in text:
        target = "tp_datadog"
    elif "redis" in text or "cache" in text or "session" in text:
        target = "cache_redis_session"
    elif "kafka" in text or "queue" in text or "stream" in text:
        target = "queue_order_kafka"
    elif "mongo" in text or "mongodb" in text:
        target = "db_catalog_mongo"
    elif "user" in text or "users" in text or "profile" in text:
        target = "svc_user"
    elif "catalog" in text or "product" in text or "items" in text:
        target = "svc_catalog"
    elif "search" in text:
        target = "svc_search"
    elif "shipping" in text or "logistics" in text:
        target = "svc_shipping"
    elif "notification" in text or "email" in text or "sms" in text:
        target = "svc_notification"
    elif "recommendation" in text:
        target = "svc_recommendation"
    elif "gateway" in text:
        target = "svc_gateway"
    else:
        target = "svc_gateway"

    return ParsedIntent(
        simulation_type=SimulationType.FAILURE,
        target_name=target,
        action="OUTAGE_SIMULATION",
        confidence=0.90,
        reasoning="Inferred e-commerce service or infrastructure failure scenario.",
    )


_VALID_TARGET_NAME = re.compile(r"^[a-zA-Z0-9_\-\.\s]{1,128}$")
_VALID_VERSION = re.compile(r"^[vV]?[0-9]+(\.[0-9]+)*(-[a-zA-Z0-9_\.]+)?$")


def parse_intent(prompt: str, settings: Settings) -> ParsedIntent:
    """Parses user prompt into structured simulation intent using Gemini, falling back gracefully."""
    api_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None

    # If no key configured, immediately use deterministic rule engine
    if not api_key:
        log.info("No Gemini API key configured, using rule-based parser")
        return _rule_based_fallback(prompt)

    try:
        from google.genai import types

        from app.agent.client import get_genai_client

        client = get_genai_client(api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        if response and response.text:
            data = json.loads(response.text.strip())
            raw_target = str(data.get("target_name", "")).strip()
            if not raw_target or not _VALID_TARGET_NAME.match(raw_target):
                log.warning("Unsafe or invalid target_name '%s' from LLM; using fallback parser", raw_target)
                return _rule_based_fallback(prompt)

            # Normalize common synonyms from LLM output
            norm_target = raw_target.lower()
            if any(k in norm_target for k in ("api key", "api-key", "apikey", "gateway", "ingress")):
                raw_target = "api-gateway"
            elif norm_target == "payment service":
                raw_target = "payment-service"
            elif norm_target == "auth service":
                raw_target = "auth-service"
            elif norm_target == "order service":
                raw_target = "order-service"
            elif norm_target == "cart service":
                raw_target = "cart-service"
            elif norm_target == "checkout service":
                raw_target = "checkout-service"
            elif norm_target == "inventory service":
                raw_target = "inventory-service"
            elif norm_target == "user service":
                raw_target = "user-service"
            elif norm_target == "shipping service":
                raw_target = "shipping-service"
            elif norm_target == "catalog service":
                raw_target = "catalog-service"
            elif norm_target == "search service":
                raw_target = "search-service"
            elif norm_target == "notification service":
                raw_target = "notification-service"
            elif norm_target == "recommendation service":
                raw_target = "recommendation-service"
            elif norm_target == "fraud service" or norm_target == "fraud detection":
                raw_target = "fraud-detection-service"
            else:
                raw_target = raw_target.replace(" ", "-")

            raw_ver = data.get("target_version")
            if raw_ver and not _VALID_VERSION.match(str(raw_ver).strip()):
                log.warning("Invalid target_version '%s' from LLM; ignoring version", raw_ver)
                raw_ver = None

            sim_type_str = data.get("simulation_type", "failure")
            try:
                sim_type = SimulationType(sim_type_str)
            except ValueError:
                sim_type = SimulationType.FAILURE

            return ParsedIntent(
                simulation_type=sim_type,
                target_name=raw_target,
                target_version=str(raw_ver).strip() if raw_ver else None,
                action=str(data.get("action", "SIMULATE"))[:64],
                confidence=0.95,
                reasoning=str(data.get("reasoning", "Parsed by Gemini Flash"))[:300],
            )
    except Exception as exc:
        log.warning("Gemini parsing failed (%s), falling back to deterministic parser", exc)

    return _rule_based_fallback(prompt)
