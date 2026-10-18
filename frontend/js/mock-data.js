/**
 * ConseQ / ECHO — Software Architecture & Failure Simulator
 * Grounded Mock Topology and Incident Reports.
 * All metrics derive from the 14-service enterprise e-commerce dependency graph:
 * - 14 Microservices across Tier 1 (Core), Tier 2 (Features), Tier 3 (Support)
 * - 6 Datastores & Caches (PostgreSQL, MongoDB, Redis, Kafka)
 * - 5 Third-Party Providers (Stripe, PayPal Backup, Twilio, SendGrid, Datadog)
 * - 9 Ingress API Endpoints
 * - 4 Shared Libraries & 5 Engineering Teams
 */

window.ARCHITECTURE_METRICS = {
  service_count: 14,
  datastore_count: 6,
  endpoint_count: 9,
  third_party_count: 5,
  library_count: 4,
  node_count: 32,
  edge_count: 48,
};

window.MOCK_TOPOLOGY = {
  nodes: [
    { id: "app_web", name: "Web Storefront", label: "ClientApp", platform: "web" },
    { id: "app_ios", name: "iOS Native App", label: "ClientApp", platform: "ios" },
    { id: "app_android", name: "Android App", label: "ClientApp", platform: "android" },
    { id: "app_partner_api", name: "B2B Ingestion API", label: "ClientApp", platform: "b2b" },

    { id: "ep_login", name: "POST /api/v1/auth/login", label: "APIEndpoint" },
    { id: "ep_get_products", name: "GET /api/v1/catalog/items", label: "APIEndpoint" },
    { id: "ep_view_cart", name: "GET /api/v1/cart", label: "APIEndpoint" },
    { id: "ep_add_cart", name: "POST /api/v1/cart/items", label: "APIEndpoint" },
    { id: "ep_checkout_submit", name: "POST /api/v1/checkout/submit", label: "APIEndpoint" },
    { id: "ep_process_payment", name: "POST /api/v1/payments/charge", label: "APIEndpoint" },
    { id: "ep_get_orders", name: "GET /api/v1/orders", label: "APIEndpoint" },

    { id: "svc_gateway", name: "api-gateway", label: "Service", tier: 1, status: "healthy" },
    { id: "svc_auth", name: "auth-service", label: "Service", tier: 1, status: "healthy" },
    { id: "svc_user", name: "user-service", label: "Service", tier: 1, status: "healthy" },
    { id: "svc_cart", name: "cart-service", label: "Service", tier: 1, status: "healthy" },
    { id: "svc_checkout", name: "checkout-service", label: "Service", tier: 1, status: "healthy" },
    { id: "svc_payment", name: "payment-service", label: "Service", tier: 1, status: "healthy" },
    { id: "svc_order", name: "order-service", label: "Service", tier: 1, status: "healthy" },
    { id: "svc_inventory", name: "inventory-service", label: "Service", tier: 1, status: "healthy" },
    { id: "svc_fraud", name: "fraud-detection-service", label: "Service", tier: 1, status: "healthy" },
    { id: "svc_catalog", name: "catalog-service", label: "Service", tier: 2, status: "healthy" },
    { id: "svc_search", name: "search-service", label: "Service", tier: 2, status: "healthy" },
    { id: "svc_shipping", name: "shipping-service", label: "Service", tier: 2, status: "healthy" },
    { id: "svc_notification", name: "notification-service", label: "Service", tier: 3, status: "healthy" },
    { id: "svc_recommendation", name: "recommendation-service", label: "Service", tier: 3, status: "healthy" },

    { id: "db_auth_pg", name: "Auth PostgreSQL", label: "Database", tier: 1 },
    { id: "db_order_pg", name: "Orders PostgreSQL", label: "Database", tier: 1 },
    { id: "db_catalog_mongo", name: "Catalog MongoDB", label: "Database", tier: 2 },
    { id: "db_inventory_pg", name: "Inventory PostgreSQL", label: "Database", tier: 1 },
    { id: "cache_redis_session", name: "Session Redis Cluster", label: "Database", tier: 1 },
    { id: "queue_order_kafka", name: "Order Kafka Stream", label: "Database", tier: 1 },

    { id: "tp_stripe", name: "Stripe Payments", label: "ThirdParty", tier: 1 },
    { id: "tp_paypal", name: "PayPal Backup Gateway", label: "ThirdParty", tier: 2 },
    { id: "tp_twilio", name: "Twilio SMS", label: "ThirdParty", tier: 2 },
    { id: "tp_sendgrid", name: "SendGrid Email", label: "ThirdParty", tier: 3 },

    { id: "lib_jwt", name: "crypto-jwt", label: "Library" },
    { id: "lib_payment_sdk", name: "fintech-payment-sdk", label: "Library" },
    { id: "lib_grpc", name: "grpc-common-proto", label: "Library" }
  ],
  links: [
    { source: "app_web", target: "ep_login", type: "CALLS" },
    { source: "app_web", target: "ep_get_products", type: "CALLS" },
    { source: "app_web", target: "ep_view_cart", type: "CALLS" },
    { source: "app_web", target: "ep_checkout_submit", type: "CALLS" },
    { source: "app_ios", target: "ep_login", type: "CALLS" },
    { source: "app_ios", target: "ep_checkout_submit", type: "CALLS" },
    { source: "app_android", target: "ep_login", type: "CALLS" },
    { source: "app_android", target: "ep_checkout_submit", type: "CALLS" },
    { source: "app_partner_api", target: "ep_get_orders", type: "CALLS" },

    { source: "ep_login", target: "svc_auth", type: "ROUTED_TO" },
    { source: "ep_get_products", target: "svc_catalog", type: "ROUTED_TO" },
    { source: "ep_view_cart", target: "svc_cart", type: "ROUTED_TO" },
    { source: "ep_add_cart", target: "svc_cart", type: "ROUTED_TO" },
    { source: "ep_checkout_submit", target: "svc_checkout", type: "ROUTED_TO" },
    { source: "ep_process_payment", target: "svc_payment", type: "ROUTED_TO" },
    { source: "ep_get_orders", target: "svc_order", type: "ROUTED_TO" },

    { source: "svc_gateway", target: "svc_auth", type: "CALLS" },
    { source: "svc_gateway", target: "svc_catalog", type: "CALLS" },
    { source: "svc_gateway", target: "svc_cart", type: "CALLS" },
    { source: "svc_gateway", target: "svc_checkout", type: "CALLS" },
    { source: "svc_auth", target: "svc_user", type: "CALLS" },
    { source: "svc_checkout", target: "svc_cart", type: "CALLS" },
    { source: "svc_checkout", target: "svc_payment", type: "CALLS" },
    { source: "svc_checkout", target: "svc_inventory", type: "CALLS" },
    { source: "svc_checkout", target: "svc_order", type: "CALLS" },
    { source: "svc_payment", target: "svc_fraud", type: "CALLS" },
    { source: "svc_order", target: "svc_notification", type: "CALLS" },
    { source: "svc_order", target: "svc_shipping", type: "CALLS" },

    { source: "svc_auth", target: "db_auth_pg", type: "CONNECTS_TO" },
    { source: "svc_order", target: "db_order_pg", type: "CONNECTS_TO" },
    { source: "svc_catalog", target: "db_catalog_mongo", type: "CONNECTS_TO" },
    { source: "svc_inventory", target: "db_inventory_pg", type: "CONNECTS_TO" },
    { source: "svc_cart", target: "cache_redis_session", type: "CONNECTS_TO" },
    { source: "svc_gateway", target: "cache_redis_session", type: "CONNECTS_TO" },
    { source: "svc_order", target: "queue_order_kafka", type: "CONNECTS_TO" },

    { source: "svc_payment", target: "tp_stripe", type: "INTEGRATES_WITH" },
    { source: "tp_paypal", target: "tp_stripe", type: "FALLBACK_FOR" },
    { source: "svc_notification", target: "tp_twilio", type: "INTEGRATES_WITH" },
    { source: "tp_sendgrid", target: "tp_twilio", type: "FALLBACK_FOR" },

    { source: "svc_auth", target: "lib_jwt", type: "USES_LIBRARY" },
    { source: "svc_user", target: "lib_jwt", type: "USES_LIBRARY" },
    { source: "svc_payment", target: "lib_payment_sdk", type: "USES_LIBRARY" }
  ]
};

window.MOCK_SCENARIOS = [
  {
    id: "scenario_stripe_timeout",
    title: "Stripe Payment Gateway Outage",
    prompt: "What happens if Stripe payment gateway goes offline?",
    target: "tp_stripe",
    badge: "Third-Party Failover"
  },
  {
    id: "scenario_redis_cart",
    title: "Redis Session Cache Failure",
    prompt: "What happens if Session Redis cluster fails?",
    target: "cache_redis_session",
    badge: "Cache Outage"
  },
  {
    id: "scenario_order_db_crash",
    title: "Orders Database Outage",
    prompt: "What happens if our orders PostgreSQL database crashes?",
    target: "db_order_pg",
    badge: "Datastore Failure"
  },
  {
    id: "scenario_jwt_upgrade",
    title: "Upgrade crypto-jwt to v3.0",
    prompt: "What if I upgrade crypto-jwt library to version 3.0.0?",
    target: "crypto-jwt",
    badge: "Dependency Bump"
  }
];

window.MOCK_REPORTS = {
  // 1. Stripe Payment Gateway Failure
  stripe: {
    id: "echo_stripe_outage",
    prompt: "What happens if Stripe payment gateway goes offline?",
    type: "recovery",
    target_entity: "Stripe Payments",
    blast_radius_score: 57.1,
    execution_time_ms: 112.4,
    fork_graph: "sim_stripe_fork",
    executive_summary: "Simulated complete failure of primary payment gateway **Stripe Payments**. The outage propagates across the checkout pipeline, degrading **57.1%** of architectural dependency paths. **2 Tier-1 services** (`payment-service`, `checkout-service`) and 2 critical payment endpoints are directly offline. An automated fallback edge to **PayPal Backup Gateway** is registered in the architecture graph and available for hot traffic failover.",
    actionable_recommendations: [
      "Engage circuit-breaker on `payment-service` to immediately reroute authorization traffic to `tp_paypal` (PayPal Backup Gateway).",
      "Page Checkout & Billing On-Call Lead (Marcus Vance) via Slack #team-checkout.",
      "Buffer pending order submissions into Apache Kafka to prevent data loss during failover transition.",
      "Review Stripe webhook health probes to automate recovery once primary connection is restored."
    ],
    outage_details: {
      target_id: "tp_stripe",
      target_name: "Stripe Payments",
      target_type: "ThirdParty",
      blast_radius_percent: 57.1,
      tier1_services_down: 2,
      tier2_services_down: 1,
      tier3_services_down: 0,
      impacted_services: [
        { id: "svc_payment", name: "payment-service", tier: 1, impact: "outage", hops_from_target: 1, team_name: "Checkout & Billing" },
        { id: "svc_checkout", name: "checkout-service", tier: 1, impact: "outage", hops_from_target: 2, team_name: "Checkout Squad" },
        { id: "svc_order", name: "order-service", tier: 1, impact: "degraded", hops_from_target: 3, team_name: "Core Platform SRE" }
      ],
      broken_endpoints: [
        { id: "ep_process_payment", path: "/api/v1/payments/charge", method: "POST", status: "outage", service_id: "svc_payment" },
        { id: "ep_checkout_submit", path: "/api/v1/checkout/submit", method: "POST", status: "outage", service_id: "svc_checkout" }
      ],
      impacted_clients: [
        { id: "app_web", name: "Web Storefront", platform: "web" },
        { id: "app_ios", name: "iOS Native App", platform: "ios" },
        { id: "app_android", name: "Android App", platform: "android" }
      ],
      impacted_teams: [
        { id: "team_checkout", name: "Checkout & Billing Team", slack_channel: "#team-checkout", oncall_lead: "Marcus Vance", reason: "Direct owner of payment-service and checkout-service" },
        { id: "team_platform", name: "Core Platform SRE Team", slack_channel: "#team-platform", oncall_lead: "Alex Rivera", reason: "Payment route failover orchestration" }
      ]
    }
  },

  // 2. Redis Session Cache Failure
  redis: {
    id: "echo_redis_outage",
    prompt: "What happens if Session Redis cluster fails?",
    type: "failure",
    target_entity: "Session Redis Cluster",
    blast_radius_score: 64.3,
    execution_time_ms: 128.1,
    fork_graph: "sim_redis_fork",
    executive_summary: "Simulated failure of **Session Redis Cluster**. The datastore outage compromises **64.3%** of active service dependencies. `cart-service` and `api-gateway` session verification layers fail, breaking cart persistence and authentication token verification across Web, iOS, and Android clients.",
    actionable_recommendations: [
      "Trigger Redis Sentinel replica promotion in secondary availability zone.",
      "Enable in-memory cookie session validation fallback in `api-gateway` to prevent cascading authentication rejection.",
      "Page Core Platform SRE Team (Alex Rivera) via Slack #team-platform.",
      "Rate-limit incoming cart requests to prevent thread starvation on cart-service workers."
    ],
    outage_details: {
      target_id: "cache_redis_session",
      target_name: "Session Redis Cluster",
      target_type: "Database",
      blast_radius_percent: 64.3,
      tier1_services_down: 2,
      tier2_services_down: 1,
      tier3_services_down: 0,
      impacted_services: [
        { id: "svc_cart", name: "cart-service", tier: 1, impact: "outage", hops_from_target: 1, team_name: "Checkout Squad" },
        { id: "svc_gateway", name: "api-gateway", tier: 1, impact: "degraded", hops_from_target: 1, team_name: "Core Platform SRE" },
        { id: "svc_checkout", name: "checkout-service", tier: 1, impact: "degraded", hops_from_target: 2, team_name: "Checkout Squad" }
      ],
      broken_endpoints: [
        { id: "ep_view_cart", path: "/api/v1/cart", method: "GET", status: "outage", service_id: "svc_cart" },
        { id: "ep_add_cart", path: "/api/v1/cart/items", method: "POST", status: "outage", service_id: "svc_cart" }
      ],
      impacted_clients: [
        { id: "app_web", name: "Web Storefront", platform: "web" },
        { id: "app_ios", name: "iOS Native App", platform: "ios" },
        { id: "app_android", name: "Android App", platform: "android" }
      ],
      impacted_teams: [
        { id: "team_checkout", name: "Checkout & Billing Team", slack_channel: "#team-checkout", oncall_lead: "Marcus Vance", reason: "Cart service state loss" },
        { id: "team_platform", name: "Core Platform SRE Team", slack_channel: "#team-platform", oncall_lead: "Alex Rivera", reason: "Redis Cluster failover" }
      ]
    }
  },

  // 3. Orders Database Outage
  order_db: {
    id: "echo_order_db_outage",
    prompt: "What happens if our orders PostgreSQL database crashes?",
    type: "failure",
    target_entity: "Orders PostgreSQL",
    blast_radius_score: 50.0,
    execution_time_ms: 104.5,
    fork_graph: "sim_order_db_fork",
    executive_summary: "Simulated primary datastore failure of **Orders PostgreSQL**. `order-service` enters degraded mode. New order transactions cannot be committed directly to the database. Incoming order events are safely rerouted to the **Order Kafka Stream** (`queue_order_kafka`) buffer to prevent data loss.",
    actionable_recommendations: [
      "Promote read-replica in secondary availability zone to primary status.",
      "Confirm Kafka order event stream consumer lag is healthy and queue buffering is active.",
      "Page Checkout & Billing On-Call Lead (Marcus Vance) and Core Platform SRE Team (Alex Rivera).",
      "Temporarily disable immediate order confirmation emails until Kafka replay completes."
    ],
    outage_details: {
      target_id: "db_order_pg",
      target_name: "Orders PostgreSQL",
      target_type: "Database",
      blast_radius_percent: 50.0,
      tier1_services_down: 1,
      tier2_services_down: 2,
      tier3_services_down: 1,
      impacted_services: [
        { id: "svc_order", name: "order-service", tier: 1, impact: "outage", hops_from_target: 1, team_name: "Checkout Squad" },
        { id: "svc_notification", name: "notification-service", tier: 3, impact: "degraded", hops_from_target: 2, team_name: "Platform SRE" }
      ],
      broken_endpoints: [
        { id: "ep_get_orders", path: "/api/v1/orders", method: "GET", status: "outage", service_id: "svc_order" }
      ],
      impacted_clients: [
        { id: "app_web", name: "Web Storefront", platform: "web" },
        { id: "app_partner_api", name: "B2B Ingestion API", platform: "b2b" }
      ],
      impacted_teams: [
        { id: "team_checkout", name: "Checkout & Billing Team", slack_channel: "#team-checkout", oncall_lead: "Marcus Vance", reason: "Order database primary offline" }
      ]
    }
  },

  // 4. Shared Library Upgrade (crypto-jwt)
  jwt: {
    id: "echo_jwt_upgrade",
    prompt: "What if I upgrade crypto-jwt library to version 3.0.0?",
    type: "upgrade",
    target_entity: "crypto-jwt",
    blast_radius_score: 0.0,
    execution_time_ms: 94.2,
    fork_graph: "sim_ephemeral",
    executive_summary: "Assessed dependency ripple effects for upgrading **crypto-jwt** from `2.4.1` to `3.0.0`. Detected **2 dependent microservices** (`auth-service`, `user-service`) and 1 owning team (#team-identity). Major version bump includes breaking signature changes in JWT decoding protocols.",
    actionable_recommendations: [
      "Deploy upgrade to 2 services in phased batches: auth-service, user-service.",
      "Run integration regression suites with Identity & Access Team (#team-identity).",
      "Verify backward compatibility of serialized tokens and API request schemas before merging."
    ],
    upgrade_details: {
      library_id: "lib_jwt",
      library_name: "crypto-jwt",
      current_version: "2.4.1",
      target_version: "3.0.0",
      is_major_breaking_bump: true,
      risk_level: "HIGH",
      dependent_services: [
        { service_id: "svc_auth", service_name: "auth-service", tier: 1 },
        { service_id: "svc_user", service_name: "user-service", tier: 1 }
      ],
      dependent_teams: [
        { id: "team_identity", name: "Identity & Access Team", slack_channel: "#team-identity", oncall_lead: "Sarah Chen" }
      ],
      recommended_upgrade_order: ["auth-service", "user-service"]
    },
    outage_details: {
      target_id: "lib_jwt",
      target_name: "crypto-jwt",
      target_type: "Library",
      blast_radius_percent: 0.0,
      tier1_services_down: 0,
      tier2_services_down: 0,
      tier3_services_down: 0,
      impacted_services: [],
      broken_endpoints: [],
      impacted_clients: [],
      impacted_teams: []
    }
  },

  // 5. Payment Service Outage
  payment_service: {
    id: "echo_payment_svc_outage",
    prompt: "What happens if payment-service goes offline?",
    type: "failure",
    target_entity: "payment-service",
    blast_radius_score: 21.4,
    execution_time_ms: 108.6,
    fork_graph: "sim_payment_fork",
    executive_summary: "Simulated outage of core Tier-1 microservice **payment-service**. Direct callers `checkout-service` and `api-gateway` degrade immediately. Transactions cannot be authorized, breaking 2 critical ingress checkout routes.",
    actionable_recommendations: [
      "Alert 2 on-call engineering teams immediately via PagerDuty/Slack (#team-checkout, #team-platform).",
      "Review circuit-breaker coverage across 2 affected services (checkout-service, api-gateway).",
      "Engage PayPal Backup Gateway fallback provider to resume checkout authorizations."
    ],
    outage_details: {
      target_id: "svc_payment",
      target_name: "payment-service",
      target_type: "Service",
      blast_radius_percent: 21.4,
      tier1_services_down: 3,
      tier2_services_down: 0,
      tier3_services_down: 0,
      impacted_services: [
        { id: "svc_checkout", name: "checkout-service", tier: 1, impact: "outage", hops_from_target: 1, team_name: "Checkout Squad" },
        { id: "svc_gateway", name: "api-gateway", tier: 1, impact: "degraded", hops_from_target: 2, team_name: "Core Platform SRE" }
      ],
      broken_endpoints: [
        { id: "ep_checkout_submit", path: "/api/v1/checkout/submit", method: "POST", status: "outage", service_id: "svc_checkout" },
        { id: "ep_process_payment", path: "/api/v1/payments/charge", method: "POST", status: "outage", service_id: "svc_payment" }
      ],
      impacted_clients: [
        { id: "app_web", name: "Web Storefront", platform: "web" },
        { id: "app_ios", name: "iOS Native App", platform: "ios" },
        { id: "app_android", name: "Android App", platform: "android" }
      ],
      impacted_teams: [
        { id: "team_checkout", name: "Checkout & Billing Team", slack_channel: "#team-checkout", oncall_lead: "Marcus Vance", reason: "Direct owner of payment-service" },
        { id: "team_platform", name: "Core Platform SRE Team", slack_channel: "#team-platform", oncall_lead: "Alex Rivera", reason: "Gateway routing degradation" }
      ]
    }
  },

  // 6. Default / Auth Failure
  default: {
    id: "echo_auth_outage",
    prompt: "What happens if our authentication service goes offline?",
    type: "failure",
    target_entity: "auth-service",
    blast_radius_score: 35.7,
    execution_time_ms: 119.8,
    fork_graph: "sim_auth_fork",
    executive_summary: "Simulated failure of **auth-service**. The outage immediately impacts **35.7%** of architectural dependency paths. **2 Tier-1 services** (`user-service`, `api-gateway`) and public login routes are non-functional, preventing client token verification and authenticated user access.",
    actionable_recommendations: [
      "Page Identity & Access Team Lead (Sarah Chen) via Slack #team-identity.",
      "Enable JWT token validation grace-period on `api-gateway` to allow active sessions to continue.",
      "Enable guest checkout bypass on `checkout-service` to maintain order processing during authentication downtime."
    ],
    outage_details: {
      target_id: "svc_auth",
      target_name: "auth-service",
      target_type: "Service",
      blast_radius_percent: 35.7,
      tier1_services_down: 2,
      tier2_services_down: 1,
      tier3_services_down: 0,
      impacted_services: [
        { id: "svc_user", name: "user-service", tier: 1, impact: "outage", hops_from_target: 1, team_name: "Identity & Access" },
        { id: "svc_gateway", name: "api-gateway", tier: 1, impact: "degraded", hops_from_target: 1, team_name: "Core Platform SRE" }
      ],
      broken_endpoints: [
        { id: "ep_login", path: "/api/v1/auth/login", method: "POST", status: "outage", service_id: "svc_auth" }
      ],
      impacted_clients: [
        { id: "app_web", name: "Web Storefront", platform: "web" },
        { id: "app_ios", name: "iOS Native App", platform: "ios" },
        { id: "app_android", name: "Android App", platform: "android" }
      ],
      impacted_teams: [
        { id: "team_identity", name: "Identity & Access Team", slack_channel: "#team-identity", oncall_lead: "Sarah Chen", reason: "Direct owner of auth-service" }
      ]
    }
  }
};

window.MOCK_FAILURE_REPORT = window.MOCK_REPORTS.default;
