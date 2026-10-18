/**
 * ConseQ / ECHO — E-Commerce Store Platform Baseline & Mock Scenarios Data
 * Models production e-commerce store architecture (ApexCommerce Cloud):
 * - Daily Gross Merchandise Value (GMV): $4,250,000 / day
 * - Peak Shopping Velocity: 450 orders / minute (~$38,025 / min revenue flow)
 * - Active Concurrent Shoppers: 105,000 sessions (Web, iOS, Android)
 * - Average Order Value (AOV): $84.50
 * - Checkout Pipeline: Web/App ➔ Gateway ➔ Cart (Redis) ➔ Checkout ➔ Stripe ➔ Orders (Postgres)
 */

window.STORE_FACTS = {
  store_name: "ApexCommerce Global Retail",
  daily_gmv: 4250000,
  peak_shoppers: 105000,
  aov: 84.50,
  orders_per_minute: 450,
  revenue_flow_per_minute: 38025,
  cart_conversion_rate: 3.2,
  payment_primary: "Stripe Elements (3DS2)",
  payment_fallback: "PayPal Instant Capture",
  session_store: "Redis Cluster (12-Node In-Memory)",
  order_db: "PostgreSQL 16 HA Cluster",
  inventory_db: "PostgreSQL Inventory Shard",
  messaging_bus: "Apache Kafka (Order Event Stream)"
};

window.MOCK_TOPOLOGY = {
  nodes: [
    { id: "app_web", name: "Web Storefront (Next.js)", label: "ClientApp", platform: "web", active_users: 45000 },
    { id: "app_ios", name: "iOS Native App", label: "ClientApp", platform: "ios", active_users: 28000 },
    { id: "app_android", name: "Android App", label: "ClientApp", platform: "android", active_users: 32000 },
    { id: "app_partner_api", name: "Marketplace & B2B Ingestion", label: "ClientApp", platform: "b2b", active_users: 1200 },
    
    { id: "ep_login", name: "POST /auth/login", label: "APIEndpoint" },
    { id: "ep_get_products", name: "GET /catalog/items", label: "APIEndpoint" },
    { id: "ep_view_cart", name: "GET /cart", label: "APIEndpoint" },
    { id: "ep_add_cart", name: "POST /cart/items", label: "APIEndpoint" },
    { id: "ep_checkout_submit", name: "POST /checkout/submit", label: "APIEndpoint" },
    { id: "ep_process_payment", name: "POST /payments/charge", label: "APIEndpoint" },
    { id: "ep_get_orders", name: "GET /orders", label: "APIEndpoint" },

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

    { id: "tp_stripe", name: "Stripe Payments (3DS2)", label: "ThirdParty", tier: 1 },
    { id: "tp_paypal", name: "PayPal Backup Gateway", label: "ThirdParty", tier: 2 },
    { id: "tp_twilio", name: "Twilio Order SMS", label: "ThirdParty", tier: 2 },
    { id: "tp_sendgrid", name: "SendGrid Receipt Email", label: "ThirdParty", tier: 3 },

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
    { source: "app_ios", target: "ep_view_cart", type: "CALLS" },
    { source: "app_ios", target: "ep_checkout_submit", type: "CALLS" },
    { source: "app_android", target: "ep_login", type: "CALLS" },
    { source: "app_android", target: "ep_view_cart", type: "CALLS" },
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
    title: "Flash Sale Stripe Gateway Timeout",
    prompt: "What happens if Stripe payment gateway experiences connection pool exhaustion during flash sale?",
    target: "tp_stripe",
    revenue_risk: "$38,025 / min",
    affected_stage: "Stage 4: Payment Capture",
    badge: "Payment Outage"
  },
  {
    id: "scenario_redis_cart",
    title: "Black Friday Cart Cache Eviction",
    prompt: "What happens if Session Redis cluster fails during peak 105k concurrent cart sessions?",
    target: "cache_redis_session",
    revenue_risk: "$38,025 / min",
    affected_stage: "Stage 2: Cart Reservation",
    badge: "Cart Collapse"
  },
  {
    id: "scenario_inventory_deadlock",
    title: "Inventory DB Row-Lock Deadlock",
    prompt: "Simulate inventory-service PostgreSQL row lock deadlock during high-concurrency cart reserve",
    target: "db_inventory_pg",
    revenue_risk: "$24,500 / min",
    affected_stage: "Stage 3: Stock Reservation",
    badge: "Inventory Lockup"
  },
  {
    id: "scenario_jwt_upgrade",
    title: "Upgrade crypto-jwt to v3.0",
    prompt: "What if I upgrade crypto-jwt library to version 3.0.0?",
    target: "crypto-jwt",
    revenue_risk: "$19,200 / min (Risk)",
    affected_stage: "Stage 1: User Session Auth",
    badge: "Library Upgrade"
  }
];

// Rich E-Commerce Failure Reports
window.MOCK_REPORTS = {
  // 1. Stripe Payment Gateway Failure
  stripe: {
    id: "echo_ecom_stripe",
    prompt: "What happens if Stripe payment gateway experiences connection pool exhaustion during flash sale?",
    type: "recovery",
    target_entity: "Stripe Payments (3DS2)",
    blast_radius_score: 71.4,
    execution_time_ms: 118.2,
    fork_graph: "sim_stripe_flashsale",
    revenue_at_risk_per_min: "$38,025",
    abandoned_carts: 105000,
    funnel_stage: "Stage 4: Payment Capture & 3DS2 Verification",
    executive_summary: "Simulated complete failure of primary payment gateway **Stripe Payments (3DS2)** during high-traffic velocity. The outage immediately impacts **71.4%** of checkout pipeline capacity. **450 orders/minute** ($38,025/min revenue flow) stall at final authorization. **105,000 active shoppers** encounter payment timeout errors. An automated **PayPal Instant Capture** fallback route is configured and ready for hot-failover.",
    actionable_recommendations: [
      "Engage automated circuit-breaker on `payment-service` to immediately reroute authorization traffic to PayPal Backup Gateway.",
      "Activate client-side retry banner informing shoppers that orders are queued and card transactions are safe.",
      "Notify Checkout & Billing On-Call Lead (Marcus Vance) via Slack #team-checkout and trigger Stripe status webhook monitor.",
      "Scale PostgreSQL Orders read-replicas to absorb backlog burst once payment gateway reconnects."
    ],
    outage_details: {
      target_id: "tp_stripe",
      target_name: "Stripe Payments",
      target_type: "ThirdParty",
      blast_radius_percent: 71.4,
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
        { id: "app_web", name: "Web Storefront (Next.js)", platform: "web", active_users: 45000 },
        { id: "app_ios", name: "iOS Native App", platform: "ios", active_users: 28000 },
        { id: "app_android", name: "Android App", platform: "android", active_users: 32000 }
      ],
      impacted_teams: [
        { id: "team_checkout", name: "Checkout & Billing Team", slack_channel: "#team-checkout", oncall_lead: "Marcus Vance", reason: "Direct owner of checkout-service and payment-service" },
        { id: "team_platform", name: "Core Platform SRE Team", slack_channel: "#team-platform", oncall_lead: "Alex Rivera", reason: "Ingress payment route failover orchestration" }
      ]
    }
  },

  // 2. Redis Session & Cart Eviction
  redis: {
    id: "echo_ecom_redis",
    prompt: "What happens if Session Redis cluster fails during peak 105k concurrent cart sessions?",
    type: "failure",
    target_entity: "Session Redis Cluster",
    blast_radius_score: 85.7,
    execution_time_ms: 132.4,
    fork_graph: "sim_redis_eviction",
    revenue_at_risk_per_min: "$38,025",
    abandoned_carts: 105000,
    funnel_stage: "Stage 2: Cart Reservation & Session State",
    executive_summary: "Simulated catastrophic loss of **Session Redis Cluster**. **105,000 active shopping carts** and customer session tokens are instantaneously evicted. Both `cart-service` and `api-gateway` session validators crash, causing an immediate **85.7% blast radius** across Web, iOS, and Android storefronts. Customers are bounced back to empty carts and unauthenticated states.",
    actionable_recommendations: [
      "Trigger Redis Sentinel automated failover to promote standby replica shard in `us-east-1b`.",
      "Enable cookie-backed local cart hydration in `app_web` and native apps so customers do not lose basket items.",
      "Rate-limit login ingress by 50% for 90 seconds to prevent a thundering herd on Auth PostgreSQL when shoppers re-authenticate.",
      "Alert Core Platform SRE Team (Alex Rivera) via PagerDuty priority 1."
    ],
    outage_details: {
      target_id: "cache_redis_session",
      target_name: "Session Redis Cluster",
      target_type: "Database",
      blast_radius_percent: 85.7,
      tier1_services_down: 3,
      tier2_services_down: 2,
      tier3_services_down: 0,
      impacted_services: [
        { id: "svc_cart", name: "cart-service", tier: 1, impact: "outage", hops_from_target: 1, team_name: "Checkout Squad" },
        { id: "svc_gateway", name: "api-gateway", tier: 1, impact: "outage", hops_from_target: 1, team_name: "Core Platform SRE" },
        { id: "svc_checkout", name: "checkout-service", tier: 1, impact: "outage", hops_from_target: 2, team_name: "Checkout Squad" }
      ],
      broken_endpoints: [
        { id: "ep_view_cart", path: "/api/v1/cart", method: "GET", status: "outage", service_id: "svc_cart" },
        { id: "ep_add_cart", path: "/api/v1/cart/items", method: "POST", status: "outage", service_id: "svc_cart" },
        { id: "ep_checkout_submit", path: "/api/v1/checkout/submit", method: "POST", status: "outage", service_id: "svc_checkout" }
      ],
      impacted_clients: [
        { id: "app_web", name: "Web Storefront (Next.js)", platform: "web", active_users: 45000 },
        { id: "app_ios", name: "iOS Native App", platform: "ios", active_users: 28000 },
        { id: "app_android", name: "Android App", platform: "android", active_users: 32000 }
      ],
      impacted_teams: [
        { id: "team_checkout", name: "Checkout & Billing Team", slack_channel: "#team-checkout", oncall_lead: "Marcus Vance", reason: "Cart service persistence down" },
        { id: "team_platform", name: "Core Platform SRE Team", slack_channel: "#team-platform", oncall_lead: "Alex Rivera", reason: "Redis Cluster cluster leader election failure" }
      ]
    }
  },

  // 3. Inventory Row-Lock Deadlock
  inventory: {
    id: "echo_ecom_inventory",
    prompt: "Simulate inventory-service PostgreSQL row lock deadlock during high-concurrency cart reserve",
    type: "failure",
    target_entity: "Inventory PostgreSQL",
    blast_radius_score: 50.0,
    execution_time_ms: 104.1,
    fork_graph: "sim_inv_deadlock",
    revenue_at_risk_per_min: "$24,500",
    abandoned_carts: 68000,
    funnel_stage: "Stage 3: SKU Inventory Lock & Stock Allocation",
    executive_summary: "Simulated row-lock deadlock in **Inventory PostgreSQL** under high flash-sale contention. `inventory-service` worker threads become exhausted, preventing SKU reservations for hot-sale merchandise. **68,000 active checkout sessions** hang at the reservation step, leading to timeout errors and cart drops.",
    actionable_recommendations: [
      "Implement optimistic locking with Redis distributed locks (Redlock) for SKU stock decrements instead of pessimistic row locks.",
      "Introduce a 30-second SKU reservation buffer before hard database commits.",
      "Notify Fulfillment & Logistics Team (Elena Rostova) to monitor backorder queue.",
      "Temporarily enable backorder allowance flag for high-demand items to prevent checkout abandonment."
    ],
    outage_details: {
      target_id: "db_inventory_pg",
      target_name: "Inventory PostgreSQL",
      target_type: "Database",
      blast_radius_percent: 50.0,
      tier1_services_down: 2,
      tier2_services_down: 0,
      tier3_services_down: 0,
      impacted_services: [
        { id: "svc_inventory", name: "inventory-service", tier: 1, impact: "outage", hops_from_target: 1, team_name: "Fulfillment & Logistics" },
        { id: "svc_checkout", name: "checkout-service", tier: 1, impact: "degraded", hops_from_target: 2, team_name: "Checkout Squad" }
      ],
      broken_endpoints: [
        { id: "ep_checkout_submit", path: "/api/v1/checkout/submit", method: "POST", status: "degraded", service_id: "svc_checkout" }
      ],
      impacted_clients: [
        { id: "app_web", name: "Web Storefront (Next.js)", platform: "web", active_users: 45000 },
        { id: "app_ios", name: "iOS Native App", platform: "ios", active_users: 28000 }
      ],
      impacted_teams: [
        { id: "team_logistics", name: "Fulfillment & Logistics Team", slack_channel: "#team-logistics", oncall_lead: "Elena Rostova", reason: "Inventory lockup" }
      ]
    }
  },

  // 4. Default / Fallback Auth Report
  default: {
    id: "echo_ecom_auth",
    prompt: "What happens if our authentication service goes offline?",
    type: "failure",
    target_entity: "auth-service",
    blast_radius_score: 57.1,
    execution_time_ms: 124.5,
    fork_graph: "sim_auth_outage",
    revenue_at_risk_per_min: "$38,025",
    abandoned_carts: 105000,
    funnel_stage: "Stage 1: Customer Identity & Token Verification",
    executive_summary: "Simulated complete failure of **auth-service**. The outage collapses **57.1%** of active store traffic. Ingress authentication endpoints are offline, preventing customer sign-ins and guest-to-account upgrades across **105,000 active shoppers**. Web, iOS, and Android applications fail token refresh calls.",
    actionable_recommendations: [
      "Alert Identity & Access Team (Sarah Chen) and Platform SRE Team immediately via Slack #team-identity.",
      "Enable anonymous / guest checkout bypass mode in `checkout-service` to allow active shoppers to complete transactions.",
      "Review JWT validation timeout on `api-gateway` to allow grace-period cached session tokens."
    ],
    outage_details: {
      target_id: "svc_auth",
      target_name: "auth-service",
      target_type: "Service",
      blast_radius_percent: 57.1,
      tier1_services_down: 2,
      tier2_services_down: 1,
      tier3_services_down: 0,
      impacted_services: [
        { id: "svc_user", name: "user-service", tier: 1, impact: "outage", hops_from_target: 1, team_name: "Identity & Access" },
        { id: "svc_gateway", name: "api-gateway", tier: 1, impact: "degraded", hops_from_target: 1, team_name: "Platform SRE" },
        { id: "svc_checkout", name: "checkout-service", tier: 1, impact: "degraded", hops_from_target: 2, team_name: "Checkout Squad" }
      ],
      broken_endpoints: [
        { id: "ep_login", path: "/api/v1/auth/login", method: "POST", status: "outage", service_id: "svc_auth" },
        { id: "ep_checkout_submit", path: "/api/v1/checkout/submit", method: "POST", status: "degraded", service_id: "svc_checkout" }
      ],
      impacted_clients: [
        { id: "app_web", name: "Web Storefront (Next.js)", platform: "web", active_users: 45000 },
        { id: "app_ios", name: "iOS Native App", platform: "ios", active_users: 28000 },
        { id: "app_android", name: "Android App", platform: "android", active_users: 32000 }
      ],
      impacted_teams: [
        { id: "team_identity", name: "Identity & Access Team", slack_channel: "#team-identity", oncall_lead: "Sarah Chen", reason: "Direct owner of auth-service and token verification" }
      ]
    }
  }
};

window.MOCK_FAILURE_REPORT = window.MOCK_REPORTS.default;
