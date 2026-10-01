"""The estate: every hand-written fact about the fictional bank.

Pure data, no logic. build/generate.py turns it (plus seeded background) into
graph/load.cypher. Everything is invented; nothing here describes a real firm.

Conventions
  tier        1 = customer-facing critical ... 3 = can wait until morning; ? = never rated
  dependency  T = hard   F = soft   ? = never classified
  options     observed   seen in traces, never declared in the catalog
              inactive   declared, but no traffic for months
              first=DATE when it appeared      chg=ID the change that added it
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Teams: name, pager, status, disbanded_on
# --------------------------------------------------------------------------
TEAMS = [
    ("Digital Channels", "digital-oncall", "active", None),
    ("Identity & Access", "iam-oncall", "active", None),
    ("Payments Platform", "payments-oncall", "active", None),
    ("Cards", "cards-oncall", "active", None),
    ("Core Banking", "core-oncall", "active", None),
    ("Data Platform", "dataplat-oncall", "active", None),
    ("Lending", "lending-oncall", "active", None),
    ("Wealth", "wealth-oncall", "active", None),
    ("Fraud & Risk", "risk-oncall", "active", None),
    ("Messaging Platform", "messaging-oncall", "active", None),
    ("Observability", "obs-oncall", "active", None),
    ("Treasury Tech", "treasury-oncall", "active", None),
    ("Merchant Services", "merchant-oncall", "active", None),
    ("Customer Support Tech", "support-oncall", "active", None),
    ("Compliance Tech", "compliance-oncall", "active", None),
    ("Security Engineering", "secops-oncall", "active", None),
    ("Cloud Platform", "cloud-oncall", "active", None),
    ("Data Science", "ds-oncall", "active", None),
    ("Marketing Tech", "martech-oncall", "active", None),
    ("Mobile Platform", "mobile-oncall", "active", None),
    ("Branch & ATM Tech", "branch-oncall", "active", None),
    ("Corporate Banking", "corpbank-oncall", "active", None),
    ("Internal Tools", None, "active", None),               # active, but nobody is on call
    ("Legacy Platform", None, "disbanded", "2025-03-31"),
    ("Shared Services", None, "disbanded", "2025-08-29"),
]

# --------------------------------------------------------------------------
# Services:  Team | name tier[!], ...        ("!" = deprecated)
# --------------------------------------------------------------------------
SERVICES_TEXT = """
Digital Channels | mobile-bff 1, web-bff 1, check-capture-svc 2, statements-svc 3, alerts-preferences-svc 3, branch-locator-svc 3, open-account-svc 2, secure-messaging-svc 3, document-upload-svc 3, content-cms-svc 3, personalization-svc 3, deep-link-svc ?
Identity & Access | auth-gateway 1, session-service 1, entitlements-svc 1, mfa-svc 1, device-trust-svc 2, password-reset-svc 1, sso-federation-svc 2, token-service 1, risk-based-auth-svc 2, consent-svc 2
Payments Platform | bill-pay-svc 2, wire-svc 1, p2p-transfer-svc 1, ach-origination-svc 2, payment-orchestrator 1, sanctions-screening 1, payee-directory-svc 2, ach-receiving-svc 2, rtp-svc 1, payment-limits-svc 1, fx-quote-svc 2, check-clearing-svc 2, payee-verification-svc 2
Cards | card-auth-svc 1, fraud-scoring-svc 1, card-dispute-svc 3, card-controls-svc 2, rewards-svc 3, tokenization-svc 1, card-issuance-svc 2, card-activation-svc 2, pin-management-svc 1, rewards-redemption-svc 3, merchant-category-svc 3, chargeback-svc 3, travel-notice-svc 3
Core Banking | ledger-svc 1, account-service 1, balance-svc 1, interest-accrual-batch 2, posting-engine 1, interest-calc-svc 2, fee-engine 2, statement-gen-batch 3, account-lifecycle-svc 2, overdraft-svc 2, gl-export-batch 3
Lending | mortgage-quote-svc 3, loan-origination-svc 2, credit-decision-svc 2, document-vault-svc 3, loan-servicing-svc 2, payment-plan-svc 3, appraisal-svc 3, underwriting-rules-svc 2, escrow-svc 3, collections-svc 3
Wealth | portfolio-view-svc 3, trade-order-svc 2, market-data-svc 2, advisor-portal-svc 3, order-routing-svc 2, portfolio-analytics-svc 3, tax-lot-svc 3, research-feed-svc 3
Fraud & Risk | risk-rules-engine 1, case-management-svc 2, device-intel-svc 2, transaction-monitoring-svc 1, case-routing-svc 3, watchlist-svc 1, velocity-rules-svc 2, model-scoring-svc 2
Messaging Platform | notification-svc 3, email-gateway 3, push-gateway 3, sms-gateway 3, template-render-svc 3, delivery-tracking-svc 3, preference-sync-svc 3, in-app-inbox-svc 3
Data Platform | customer-profile-svc 1, reference-data-svc 2, feature-flag-svc 2, data-catalog-svc 3, identity-resolution-svc 2, event-schema-registry 2, lookup-service 2, customer-segments-svc 3
Observability | tracing-collector 2, metrics-gateway 2, log-pipeline 2, alert-router 1, status-page-svc ?
Treasury Tech | liquidity-forecast-svc 2, cash-position-svc 2, treasury-reporting-svc 3, fx-hedging-svc 3, sweep-engine 2
Merchant Services | merchant-onboarding-svc 3, terminal-mgmt-svc 3, settlement-svc 2, merchant-portal-svc 3, acquiring-gateway 1, dispute-evidence-svc 3
Customer Support Tech | agent-desktop-svc 2, case-notes-svc 3, call-routing-svc 2, chat-gateway 3, knowledge-base-svc 3, screen-pop-svc 3
Compliance Tech | kyc-svc 1, aml-screening-svc 1, regulatory-reporting-batch 2, audit-log-svc 2, consent-ledger 3
Security Engineering | secrets-vault 1, certificate-manager 1, waf-gateway 1, siem-ingest 2, key-management-svc 1
Cloud Platform | service-mesh 1, api-gateway 1, dns-service 1, container-registry 2, config-service 1, load-balancer-mgmt 2
Data Science | model-registry 3, feature-pipeline 3, batch-scoring-svc 3, experiment-tracker ?
Marketing Tech | campaign-svc 3, offers-engine 3, audience-builder 3, email-journeys-svc 3
Mobile Platform | push-registration-svc 2, app-config-svc 2, crash-reporting-svc 3, device-attestation-svc 2
Branch & ATM Tech | atm-switch 1, cash-forecast-svc 3, branch-queue-svc 3, teller-app-svc 2, appointment-svc 3
Corporate Banking | cash-mgmt-portal 2, lockbox-svc 3, payroll-svc 2, positive-pay-svc 2, trade-finance-svc 3
Internal Tools | ops-dashboard 3, runbook-portal 3, deploy-orchestrator 2, ticketing-svc 3
Legacy Platform | legacy-profile-lookup 3!, batch-scheduler 2, legacy-ldap-bridge 2!, legacy-batch-bridge 3!, mainframe-adapter 2, notifications-legacy-svc 3!
Shared Services | shared-file-transfer 3, legacy-scheduler-ui ?, vendor-gateway 2, auth-proxy 2!
"""

# --------------------------------------------------------------------------
# Datastores:  Team | name kind tier, ...      ("(nobody)" = nobody claimed it)
# tier is the DECLARED tier.
# --------------------------------------------------------------------------
DATASTORES_TEXT = """
Data Platform | profile-cache redis 3, profile-db postgres 1, event-bus kafka 2, feature-flags-redis redis 3, reference-data-db postgres 2, lookup-cache redis 3, segments-store postgres 3, schema-registry-db postgres 2
Identity & Access | session-store redis 1, device-trust-db postgres 2, token-db postgres 1, consent-db postgres 2
Payments Platform | payments-db postgres 1, payee-db postgres 2, limits-db postgres 1, ach-batches-store object 2, fx-rates-cache redis 2
Cards | cards-db postgres 1, rewards-db mongodb 3, card-issuance-db postgres 2, pin-vault vault 1, rewards-redemption-db mongodb 3
Core Banking | ledger-db oracle 1, accounts-db oracle 1, posting-journal oracle 1, fee-config-db postgres 2, statements-store object 3
Lending | loans-db postgres 2, servicing-db postgres 2, underwriting-cache redis 3
Digital Channels | image-store object 2, content-store object 3
Wealth | market-data-cache redis 3, orders-db postgres 2, research-store object 3
Fraud & Risk | risk-features-store redis 2, case-db postgres 3, tm-alerts-db postgres 2, watchlist-cache redis 1
Messaging Platform | delivery-db postgres 3, templates-store object 3
Observability | metrics-tsdb tsdb 2, logs-index search 2
Cloud Platform | config-db etcd 1, dns-zone-store postgres 1
Security Engineering | vault-storage vault 1
Customer Support Tech | case-notes-db postgres 3, call-recordings-store object 3
Treasury Tech | positions-db postgres 2
Merchant Services | settlement-db postgres 2
Branch & ATM Tech | atm-journal-db postgres 1
Corporate Banking | payroll-db postgres 2
Compliance Tech | audit-store postgres 2, kyc-db postgres 1
Legacy Platform | legacy-profile-extract oracle 3
(nobody) | docs-store object ?, uploads-store object 3
"""

# --------------------------------------------------------------------------
# Dependencies, core (the planted story lives here).  src -> dst FLAG [options]
# --------------------------------------------------------------------------
EDGES_CORE = """
mobile-bff -> auth-gateway T
mobile-bff -> bill-pay-svc F
mobile-bff -> wire-svc F
mobile-bff -> p2p-transfer-svc F
mobile-bff -> balance-svc F
mobile-bff -> statements-svc F
mobile-bff -> card-controls-svc F
mobile-bff -> card-dispute-svc F
mobile-bff -> check-capture-svc F
mobile-bff -> loan-origination-svc F
mobile-bff -> alerts-preferences-svc F
mobile-bff -> feature-flag-svc ? observed
mobile-bff -> legacy-ldap-bridge T inactive
web-bff -> auth-gateway T
web-bff -> bill-pay-svc F
web-bff -> wire-svc F
web-bff -> p2p-transfer-svc F
web-bff -> balance-svc F
web-bff -> statements-svc F
web-bff -> loan-origination-svc F
web-bff -> trade-order-svc F
web-bff -> portfolio-view-svc F
web-bff -> feature-flag-svc ? observed
web-bff -> legacy-ldap-bridge T inactive
auth-gateway -> session-service T
auth-gateway -> entitlements-svc T
auth-gateway -> mfa-svc T
mfa-svc -> device-trust-svc F
mfa-svc -> sms-gateway F
mfa-svc -> push-gateway F
session-service -> session-store T
device-trust-svc -> device-trust-db T
device-trust-svc -> device-intel-svc F observed
entitlements-svc -> customer-profile-svc ? observed first=2025-06-03 chg=CHG-1873
entitlements-svc -> reference-data-svc F
customer-profile-svc -> profile-cache T first=2023-02-14
customer-profile-svc -> profile-db T first=2023-02-14
customer-profile-svc -> reference-data-svc F
reference-data-svc -> reference-data-db T
feature-flag-svc -> feature-flags-redis T
legacy-profile-lookup -> customer-profile-svc ? observed first=2024-11-02
legacy-profile-lookup -> legacy-profile-extract T
sanctions-screening -> legacy-profile-lookup ? observed
payee-directory-svc -> legacy-profile-lookup ? observed
bill-pay-svc -> payment-orchestrator T
bill-pay-svc -> entitlements-svc T
bill-pay-svc -> payee-directory-svc T
bill-pay-svc -> notification-svc F
bill-pay-svc -> feature-flag-svc ? observed
p2p-transfer-svc -> payment-orchestrator T
p2p-transfer-svc -> entitlements-svc T
p2p-transfer-svc -> payee-directory-svc T
p2p-transfer-svc -> account-service T
ach-origination-svc -> payment-orchestrator T
ach-origination-svc -> entitlements-svc T
wire-svc -> payment-orchestrator T
wire-svc -> sanctions-screening T
wire-svc -> entitlements-svc T
wire-svc -> notification-svc F
wire-svc -> feature-flag-svc ? observed
sanctions-screening -> customer-profile-svc T
sanctions-screening -> reference-data-svc T
payee-directory-svc -> payee-db T
payee-directory-svc -> customer-profile-svc F
payment-orchestrator -> ledger-svc T
payment-orchestrator -> payments-db T
payment-orchestrator -> risk-rules-engine T
ledger-svc -> ledger-db T
ledger-svc -> event-bus F
account-service -> accounts-db T
account-service -> ledger-svc T
balance-svc -> account-service T
interest-accrual-batch -> ledger-svc T
interest-accrual-batch -> batch-scheduler T
card-auth-svc -> fraud-scoring-svc T
card-auth-svc -> cards-db T
card-auth-svc -> ledger-svc T
card-auth-svc -> tokenization-svc T
card-auth-svc -> feature-flag-svc ? observed
fraud-scoring-svc -> customer-profile-svc F
fraud-scoring-svc -> event-bus F
fraud-scoring-svc -> risk-features-store T
fraud-scoring-svc -> device-intel-svc F
tokenization-svc -> cards-db T
card-controls-svc -> cards-db T
card-controls-svc -> entitlements-svc T
card-dispute-svc -> cards-db T
card-dispute-svc -> ledger-svc T
card-dispute-svc -> notification-svc F
card-dispute-svc -> case-management-svc F
rewards-svc -> rewards-db T
rewards-svc -> cards-db F
check-capture-svc -> image-store T
check-capture-svc -> ledger-svc T
check-capture-svc -> notification-svc F
check-capture-svc -> risk-rules-engine F
statements-svc -> account-service T
statements-svc -> document-vault-svc T
alerts-preferences-svc -> customer-profile-svc T
alerts-preferences-svc -> notification-svc F
branch-locator-svc -> reference-data-svc T
mortgage-quote-svc -> credit-decision-svc F
mortgage-quote-svc -> reference-data-svc T
loan-origination-svc -> credit-decision-svc T
loan-origination-svc -> document-vault-svc T
loan-origination-svc -> loans-db T
loan-origination-svc -> entitlements-svc T
loan-origination-svc -> customer-profile-svc T
credit-decision-svc -> loans-db T
credit-decision-svc -> reference-data-svc T
credit-decision-svc -> event-bus F
document-vault-svc -> docs-store T
portfolio-view-svc -> account-service T
portfolio-view-svc -> market-data-svc T
trade-order-svc -> market-data-svc T
trade-order-svc -> ledger-svc T
trade-order-svc -> entitlements-svc T
trade-order-svc -> feature-flag-svc ? observed
market-data-svc -> market-data-cache T
risk-rules-engine -> risk-features-store T
risk-rules-engine -> device-intel-svc F
device-intel-svc -> risk-features-store T
device-intel-svc -> risk-rules-engine F observed
case-management-svc -> case-db T
case-management-svc -> event-bus F
case-management-svc -> notification-svc F
notification-svc -> case-management-svc F observed
notification-svc -> alerts-preferences-svc F observed
notification-svc -> event-bus T
notification-svc -> email-gateway F
notification-svc -> push-gateway F
notification-svc -> sms-gateway F
"""

# --------------------------------------------------------------------------
# Dependencies, the rest of the estate.   src: dst FLAG [options]; dst FLAG; ...
# --------------------------------------------------------------------------
EDGES_ESTATE = """
auth-gateway: token-service T; risk-based-auth-svc F; sso-federation-svc F observed
mobile-bff: push-registration-svc F; app-config-svc ? observed; personalization-svc F; open-account-svc F; secure-messaging-svc F; deep-link-svc F
web-bff: open-account-svc F; content-cms-svc F; personalization-svc F; secure-messaging-svc F; advisor-portal-svc F
bill-pay-svc: payment-limits-svc T; notifications-legacy-svc F inactive
p2p-transfer-svc: payment-limits-svc T; notification-svc F
wire-svc: fx-quote-svc F
payment-orchestrator: payment-limits-svc T
card-auth-svc: merchant-category-svc F
risk-rules-engine: velocity-rules-svc F
statements-svc: statements-store T
notification-svc: template-render-svc T; delivery-tracking-svc F; preference-sync-svc F
check-capture-svc: notifications-legacy-svc F observed
statement-gen-batch: accounts-db T; statements-store T; batch-scheduler T; legacy-batch-bridge T inactive
interest-accrual-batch: legacy-batch-bridge F inactive

open-account-svc: kyc-svc T; document-upload-svc T; identity-resolution-svc T; account-lifecycle-svc T; notification-svc F; customer-profile-svc F
secure-messaging-svc: entitlements-svc T; in-app-inbox-svc T; notification-svc F
document-upload-svc: uploads-store T; entitlements-svc T; audit-log-svc F
content-cms-svc: content-store T
personalization-svc: customer-segments-svc T; offers-engine F; entitlements-svc F
deep-link-svc: app-config-svc F

password-reset-svc: identity-resolution-svc T; token-service T; notification-svc T; mfa-svc F
sso-federation-svc: token-service T; consent-svc F; entitlements-svc T
token-service: token-db T; key-management-svc T
risk-based-auth-svc: device-trust-svc T; risk-rules-engine F; model-scoring-svc F
consent-svc: consent-db T; consent-ledger F

ach-receiving-svc: payment-orchestrator T; ach-batches-store T
rtp-svc: payment-orchestrator T; sanctions-screening T; payment-limits-svc T; entitlements-svc T
payment-limits-svc: limits-db T; customer-profile-svc F
fx-quote-svc: fx-rates-cache T; reference-data-svc T; entitlements-svc T
check-clearing-svc: ledger-svc T; image-store T; risk-rules-engine F
payee-verification-svc: payee-directory-svc T; customer-profile-svc T

card-issuance-svc: card-issuance-db T; tokenization-svc T; entitlements-svc T; kyc-svc T
card-activation-svc: cards-db T; pin-management-svc T; entitlements-svc T
pin-management-svc: pin-vault T; key-management-svc T
rewards-redemption-svc: rewards-redemption-db T; rewards-svc T; entitlements-svc T; offers-engine F
merchant-category-svc: reference-data-svc T
chargeback-svc: cards-db T; case-management-svc T; ledger-svc T; dispute-evidence-svc F
travel-notice-svc: cards-db T; entitlements-svc T; fraud-scoring-svc F

posting-engine: posting-journal T; ledger-svc T; fee-engine F
interest-calc-svc: accounts-db T; ledger-svc T; reference-data-svc T
fee-engine: fee-config-db T; account-lifecycle-svc F
account-lifecycle-svc: accounts-db T; ledger-svc T; kyc-svc F
overdraft-svc: accounts-db T; ledger-svc T; fee-engine T; customer-profile-svc F
gl-export-batch: ledger-svc T; batch-scheduler T; regulatory-reporting-batch F

loan-servicing-svc: servicing-db T; ledger-svc T; entitlements-svc T; payment-orchestrator T; collections-svc F
payment-plan-svc: servicing-db T; loan-servicing-svc T
appraisal-svc: loans-db T; vendor-gateway T
underwriting-rules-svc: loans-db T; underwriting-cache F; credit-decision-svc T; reference-data-svc T
escrow-svc: servicing-db T; ledger-svc T
collections-svc: servicing-db T; notification-svc F; customer-profile-svc T

advisor-portal-svc: portfolio-view-svc T; secure-messaging-svc F; entitlements-svc T
order-routing-svc: orders-db T; market-data-svc T; trade-order-svc T
portfolio-analytics-svc: portfolio-view-svc T; research-feed-svc F
tax-lot-svc: orders-db T; ledger-svc T
research-feed-svc: research-store T

transaction-monitoring-svc: tm-alerts-db T; risk-rules-engine T; model-scoring-svc T; case-routing-svc F; event-bus T
case-routing-svc: case-management-svc T; ticketing-svc F
watchlist-svc: watchlist-cache T; reference-data-svc T
velocity-rules-svc: risk-features-store T; watchlist-svc F
model-scoring-svc: model-registry T; feature-pipeline F; risk-features-store T
case-management-svc: case-routing-svc F observed

template-render-svc: templates-store T
delivery-tracking-svc: delivery-db T; email-gateway F; push-gateway F; sms-gateway F
preference-sync-svc: customer-profile-svc ? observed; consent-svc F
in-app-inbox-svc: delivery-db T; template-render-svc T

data-catalog-svc: schema-registry-db T
identity-resolution-svc: profile-db T; lookup-cache F; reference-data-svc F
event-schema-registry: schema-registry-db T
lookup-service: lookup-cache T; reference-data-svc T
customer-segments-svc: segments-store T; customer-profile-svc T

metrics-gateway: metrics-tsdb T
log-pipeline: logs-index T
alert-router: ticketing-svc F; event-bus T; metrics-gateway T
status-page-svc: alert-router F

legacy-batch-bridge: mainframe-adapter T; batch-scheduler T
mainframe-adapter: legacy-profile-extract T

liquidity-forecast-svc: positions-db T; ledger-svc T; cash-position-svc T
cash-position-svc: positions-db T; ledger-svc T
treasury-reporting-svc: positions-db T; regulatory-reporting-batch F
fx-hedging-svc: positions-db T; fx-quote-svc T
sweep-engine: cash-position-svc T; payment-orchestrator T

merchant-onboarding-svc: kyc-svc T; settlement-db T; entitlements-svc F
terminal-mgmt-svc: settlement-db T; device-attestation-svc F
settlement-svc: settlement-db T; ledger-svc T; acquiring-gateway T
merchant-portal-svc: entitlements-svc T; settlement-svc T; merchant-onboarding-svc F
acquiring-gateway: card-auth-svc T; tokenization-svc T
dispute-evidence-svc: case-notes-svc F; document-upload-svc F

agent-desktop-svc: customer-profile-svc ? observed; case-notes-svc T; knowledge-base-svc F; call-routing-svc F
case-notes-svc: case-notes-db T
call-routing-svc: call-recordings-store F; agent-desktop-svc F observed
chat-gateway: agent-desktop-svc T; entitlements-svc T; secure-messaging-svc F
knowledge-base-svc: content-store F
screen-pop-svc: customer-profile-svc ? observed; call-routing-svc T

kyc-svc: kyc-db T; identity-resolution-svc T; watchlist-svc T; document-upload-svc F
aml-screening-svc: watchlist-svc T; transaction-monitoring-svc T; case-management-svc F
regulatory-reporting-batch: audit-store T; batch-scheduler T; ledger-svc T; shared-file-transfer T
audit-log-svc: audit-store T; event-bus F
consent-ledger: audit-store T

secrets-vault: vault-storage T
certificate-manager: vault-storage T; secrets-vault T
waf-gateway: dns-service T
siem-ingest: logs-index T; event-bus T
key-management-svc: vault-storage T; secrets-vault T

service-mesh: config-service T; certificate-manager T
api-gateway: service-mesh T; token-service T; waf-gateway T
dns-service: dns-zone-store T
config-service: config-db T; service-mesh F observed
load-balancer-mgmt: dns-service T; config-service T

batch-scoring-svc: model-registry T; feature-pipeline T
feature-pipeline: lookup-cache F
experiment-tracker: model-registry F

campaign-svc: audience-builder T; email-journeys-svc F; offers-engine T
offers-engine: customer-segments-svc T; reference-data-svc F
audience-builder: customer-segments-svc T
email-journeys-svc: template-render-svc T; email-gateway T; consent-svc T

push-registration-svc: push-gateway T; device-attestation-svc F; token-service F
app-config-svc: feature-flag-svc ? observed; config-service F
crash-reporting-svc: log-pipeline F
device-attestation-svc: device-trust-svc T

atm-switch: card-auth-svc T; pin-management-svc T; atm-journal-db T; cash-forecast-svc F
cash-forecast-svc: atm-journal-db T; model-registry F
branch-queue-svc: appointment-svc F
teller-app-svc: entitlements-svc T; account-service T; ledger-svc T; customer-profile-svc T; auth-proxy T observed
appointment-svc: customer-profile-svc F; notification-svc F

cash-mgmt-portal: entitlements-svc T; cash-position-svc T; payment-orchestrator T; lockbox-svc F
lockbox-svc: ledger-svc T; image-store T; shared-file-transfer T
payroll-svc: entitlements-svc T; payment-orchestrator T; payroll-db T; ach-origination-svc T
positive-pay-svc: check-clearing-svc T; entitlements-svc T
trade-finance-svc: ledger-svc T; document-vault-svc T

ops-dashboard: metrics-gateway T; alert-router F; runbook-portal F
runbook-portal: content-store F
deploy-orchestrator: config-service T; container-registry T; ticketing-svc F

shared-file-transfer: vendor-gateway T
legacy-scheduler-ui: batch-scheduler T
auth-proxy: auth-gateway T
notifications-legacy-svc: email-gateway T
"""

# Every service reports to the tracing collector: seen in traces, soft, never declared.
NO_TRACING = {"tracing-collector", "email-gateway", "push-gateway", "sms-gateway", "container-registry",
              "legacy-profile-lookup", "batch-scheduler", "legacy-ldap-bridge", "auth-proxy", "vendor-gateway"}

# --------------------------------------------------------------------------
# Journeys: name, daily attempts, owning team, required services, profile
# profile = share of daily attempts in the hour at (03:00, 07:00, 12:00); invented.
# --------------------------------------------------------------------------
P = (0.005, 0.050, 0.070)
JOURNEYS = [
    ("Log in",                  2_400_000, "Identity & Access", ["auth-gateway"], P),
    ("Check a balance",         1_600_000, "Digital Channels",  ["auth-gateway", "balance-svc"], P),
    ("Tap to pay",              1_900_000, "Cards",             ["card-auth-svc"], (0.012, 0.040, 0.080)),
    ("Transfer money",            420_000, "Payments Platform", ["auth-gateway", "p2p-transfer-svc"], P),
    ("Pay a bill",                310_000, "Payments Platform", ["auth-gateway", "bill-pay-svc"], (0.004, 0.045, 0.065)),
    ("Deposit a check",           220_000, "Digital Channels",  ["auth-gateway", "check-capture-svc"], (0.003, 0.040, 0.080)),
    ("Download a statement",       95_000, "Digital Channels",  ["auth-gateway", "statements-svc"], P),
    ("Update contact details",     85_000, "Digital Channels",  ["auth-gateway", "alerts-preferences-svc"], P),
    ("Freeze a card",              60_000, "Cards",             ["auth-gateway", "card-controls-svc"], (0.010, 0.040, 0.060)),
    ("Send a wire",                45_000, "Payments Platform", ["auth-gateway", "wire-svc"], (0.001, 0.030, 0.090)),
    ("Place a trade",              38_000, "Wealth",            ["auth-gateway", "trade-order-svc"], (0.001, 0.010, 0.080)),
    ("Dispute a charge",           28_000, "Cards",             ["auth-gateway", "card-dispute-svc"], P),
    ("Apply for a mortgage",        6_000, "Lending",           ["auth-gateway", "loan-origination-svc"], (0.0005, 0.020, 0.090)),
    ("Open an account",            52_000, "Digital Channels",  ["open-account-svc", "kyc-svc"], (0.002, 0.030, 0.080)),
    ("Reset a password",          140_000, "Identity & Access", ["password-reset-svc"], (0.008, 0.050, 0.060)),
    ("Add a payee",               120_000, "Payments Platform", ["auth-gateway", "payee-directory-svc"], P),
    ("Redeem rewards",             44_000, "Cards",             ["auth-gateway", "rewards-redemption-svc"], P),
    ("Set a travel notice",        31_000, "Cards",             ["auth-gateway", "travel-notice-svc"], (0.002, 0.020, 0.060)),
    ("Chat with support",         210_000, "Customer Support Tech", ["auth-gateway", "chat-gateway"], (0.006, 0.040, 0.075)),
    ("Find a branch or ATM",      260_000, "Branch & ATM Tech", ["branch-locator-svc"], (0.004, 0.030, 0.090)),
    ("Withdraw cash at an ATM",   780_000, "Branch & ATM Tech", ["atm-switch"], (0.015, 0.045, 0.075)),
    ("Make a loan payment",       170_000, "Lending",           ["auth-gateway", "loan-servicing-svc"], P),
    ("Set up autopay",             90_000, "Payments Platform", ["auth-gateway", "bill-pay-svc", "payment-limits-svc"], P),
    ("Pay a credit card",         530_000, "Payments Platform", ["auth-gateway", "ach-origination-svc"], P),
    ("Run payroll",                14_000, "Corporate Banking", ["auth-gateway", "payroll-svc"], (0.001, 0.030, 0.090)),
    ("Approve positive pay",        9_000, "Corporate Banking", ["auth-gateway", "positive-pay-svc"], (0.001, 0.040, 0.080)),
    ("View merchant settlements",  21_000, "Merchant Services", ["auth-gateway", "merchant-portal-svc", "settlement-svc"], (0.001, 0.030, 0.080)),
    ("Get an FX quote",            17_000, "Payments Platform", ["auth-gateway", "fx-quote-svc"], (0.003, 0.030, 0.080)),
    ("Message my advisor",         23_000, "Wealth",            ["auth-gateway", "secure-messaging-svc", "advisor-portal-svc"], (0.001, 0.020, 0.070)),
    ("Visit a branch teller",      66_000, "Branch & ATM Tech", ["teller-app-svc"], (0.000, 0.010, 0.090)),
]

# --------------------------------------------------------------------------
# Tonight's alert storm: 19 alerts, 11 teams, 03:07 to 03:14.
# The cause, its symptoms (including two nobody expects), and eight unrelated.
# --------------------------------------------------------------------------
ALERTS = [  # id, time, component, summary
    ("ALR-77120", "03:07", "profile-cache",        "profile-cache p99 latency 4.2s, hit rate 31% and falling"),
    ("ALR-77121", "03:08", "customer-profile-svc", "customer-profile-svc p99 latency 2.9s"),
    ("ALR-77122", "03:08", "image-store",          "image-store disk usage 78%"),
    ("ALR-77123", "03:09", "entitlements-svc",     "entitlements-svc error rate 6%"),
    ("ALR-77124", "03:09", "auth-gateway",         "auth-gateway 5xx rate 4%"),
    ("ALR-77125", "03:10", "wire-svc",             "wire-svc submission timeouts"),
    ("ALR-77126", "03:10", "wire-svc",             "wire-svc retry storm: queue depth 4x"),
    ("ALR-77127", "03:11", "sanctions-screening",  "sanctions-screening latency above SLO"),
    ("ALR-77128", "03:11", "logs-index",           "logs-index disk usage 81%"),
    ("ALR-77129", "03:11", "settlement-db",        "settlement-db replication lag 40s"),
    ("ALR-77130", "03:12", "bill-pay-svc",         "bill-pay-svc error rate 9%"),
    ("ALR-77131", "03:12", "email-gateway",        "email-gateway bounce rate 3%"),
    ("ALR-77132", "03:12", "campaign-svc",         "campaign-svc audience refresh failing"),
    ("ALR-77133", "03:13", "mobile-bff",           "mobile-bff login failures rising"),
    ("ALR-77134", "03:13", "atm-journal-db",       "atm-journal-db connections at 85% of pool"),
    ("ALR-77135", "03:13", "trade-finance-svc",    "trade-finance-svc end-of-day batch late"),
    ("ALR-77136", "03:14", "agent-desktop-svc",    "agent-desktop-svc slow screen pops"),
    ("ALR-77137", "03:14", "push-gateway",         "push-gateway delivery latency 2x"),
    ("ALR-77138", "03:14", "metrics-tsdb",         "metrics-tsdb ingestion lag 90s"),
]

# --------------------------------------------------------------------------
# Runbooks written by hand: id, covers, last reviewed. The generator adds more.
# Nothing ever covers profile-cache, customer-profile-svc or entitlements-svc.
# --------------------------------------------------------------------------
RUNBOOKS = [
    ("RB-wire-timeouts", ["wire-svc"], "2024-02-12"),
    ("RB-login-latency", ["auth-gateway"], "2026-04-01"),
    ("RB-ledger-failover", ["ledger-svc", "ledger-db"], "2026-07-10"),
    ("RB-session-store", ["session-store"], "2025-11-20"),
    ("RB-card-declines", ["card-auth-svc"], "2026-02-15"),
    ("RB-payment-orchestrator-backlog", ["payment-orchestrator"], "2025-02-01"),
    ("RB-event-bus-lag", ["event-bus"], "2026-05-05"),
    ("RB-image-store-disk", ["image-store"], "2025-09-09"),
    ("RB-sanctions-screening-down", ["sanctions-screening"], "2024-08-30"),
    ("RB-mobile-bff-errors", ["mobile-bff"], "2026-01-20"),
    ("RB-accounts-db-failover", ["accounts-db"], "2026-03-14"),
    ("RB-notification-backlog", ["notification-svc"], "2025-12-02"),
    ("RB-cards-db-failover", ["cards-db"], "2026-06-01"),
    ("RB-risk-rules-engine", ["risk-rules-engine"], "2025-05-05"),
]
# Never given a runbook, however the generator rolls.
NEVER_COVERED = {"profile-cache", "customer-profile-svc", "entitlements-svc", "legacy-profile-lookup",
                 "alerts-preferences-svc", "loan-origination-svc", "auth-proxy", "legacy-profile-extract"}

# --------------------------------------------------------------------------
# Planted incidents. Six were caused by profile-cache since the dependency was born,
# every one misrouted. INC-1099 is the control: routed straight to its owner.
# --------------------------------------------------------------------------
PLANTED_INCIDENTS = [
    dict(id="INC-1041", at="2025-07-08T09:20:00Z", sev=3, title="Payee lookups timing out", root="profile-cache",
         affected=["bill-pay-svc", "payee-directory-svc"], team="Payments Platform", minutes=190, impact="degraded",
         customers=18_000, reassignments=2, detail="Cache evictions; hit rate fell to 44%"),
    dict(id="INC-1058", at="2025-10-21T14:05:00Z", sev=2, title="Wire submissions timing out", root="profile-cache",
         affected=["wire-svc", "sanctions-screening"], team="Payments Platform", minutes=215, impact="degraded",
         customers=9_000, reassignments=3, detail="Cache evictions; hit rate fell to 41%"),
    dict(id="INC-1077", at="2026-01-14T11:30:00Z", sev=3, title="Login latency spikes", root="profile-cache",
         affected=["auth-gateway", "entitlements-svc"], team="Identity & Access", minutes=160, impact="degraded",
         customers=520_000, reassignments=2, detail="Cache evictions; hit rate fell to 38%; logins slow but succeeded"),
    dict(id="INC-1093", at="2026-03-30T16:45:00Z", sev=2, title="Mortgage applications failing", root="profile-cache",
         affected=["loan-origination-svc"], team="Lending", minutes=305, impact="outage",
         customers=3_100, reassignments=4, detail="Cache evictions; hit rate fell to 21%"),
    dict(id="INC-1120", at="2026-06-17T08:10:00Z", sev=3, title="Contact-detail updates erroring", root="profile-cache",
         affected=["alerts-preferences-svc"], team="Digital Channels", minutes=175, impact="degraded",
         customers=74_000, reassignments=3, detail="Cache evictions; hit rate fell to 36%"),
    dict(id="INC-1135", at="2026-08-11T18:30:00Z", sev=1, title="Customers cannot log in or pay bills", root="profile-cache",
         affected=["mobile-bff", "auth-gateway", "bill-pay-svc"], team="Digital Channels", minutes=280, impact="outage",
         customers=1_200_000, reassignments=5, detail="Cache evictions; hit rate fell to 9%; entitlements-svc failed rather than slowed"),
    dict(id="INC-1099", at="2026-05-19T01:40:00Z", sev=2, title="Tap to pay declines", root="fraud-scoring-svc",
         affected=["card-auth-svc"], team="Cards", minutes=52, impact="outage",
         customers=61_000, reassignments=0, detail="Bad deploy (CHG-2210); rolled back"),
]

# --------------------------------------------------------------------------
# Planted changes: id, at, service, what, risk_review
# --------------------------------------------------------------------------
PLANTED_CHANGES = [
    ("CHG-1873", "2025-06-03T15:20:00Z", "entitlements-svc", "Resolve group membership via customer-profile-svc", False),
    ("CHG-2210", "2026-05-18T23:30:00Z", "fraud-scoring-svc", "Deploy v4.12", True),
    ("CHG-2288", "2026-09-20T15:00:00Z", "ledger-svc", "Deploy v7.3", True),
    ("CHG-2299", "2026-09-29T14:00:00Z", "bill-pay-svc", "Deploy v2.8", True),
    ("CHG-2301", "2026-09-29T22:15:00Z", "customer-profile-svc", "Config: profile cache TTL 24h to 1h", False),
    ("CHG-2303", "2026-09-29T20:00:00Z", "card-dispute-svc", "Deploy v1.9", True),
    ("CHG-2304", "2026-09-29T19:40:00Z", "entitlements-svc", "Dependency upgrade: http client 4.2", True),
    ("CHG-2305", "2026-09-30T01:10:00Z", "tracing-collector", "Config: sampling rate 10% to 5%", True),
    ("CHG-2306", "2026-09-29T17:00:00Z", "mobile-bff", "Feature flag rollout: new login screen 25%", True),
]
# Random overnight changes must not land close to the cache, or CHG-2301 stops being the clear suspect.
KEEP_CLEAR_OF = {"customer-profile-svc", "entitlements-svc", "sanctions-screening", "legacy-profile-lookup",
                 "alerts-preferences-svc", "loan-origination-svc", "preference-sync-svc", "agent-desktop-svc",
                 "screen-pop-svc", "payee-verification-svc", "collections-svc", "customer-segments-svc",
                 "teller-app-svc", "profile-cache"}

# --------------------------------------------------------------------------
# THE EASTER EGG (spoiler; not mentioned in the guide).
# A wildcard certificate nobody owns expires in eight days, under most of the estate.
# --------------------------------------------------------------------------
WILDCARD = dict(
    name="wildcard.internal.bank", expires_on="2026-10-08", last_rotated="2025-10-10", auto_renew=False,
    issuer="Internal CA", team="Shared Services",
    used_by=["api-gateway", "service-mesh", "auth-gateway", "session-service", "entitlements-svc", "ledger-svc",
             "account-service", "payment-orchestrator", "card-auth-svc", "fraud-scoring-svc", "tokenization-svc",
             "wire-svc", "bill-pay-svc", "p2p-transfer-svc", "risk-rules-engine", "customer-profile-svc",
             "notification-svc", "mobile-bff", "web-bff", "sanctions-screening", "balance-svc", "posting-engine",
             "rtp-svc", "kyc-svc", "aml-screening-svc", "acquiring-gateway", "atm-switch", "loan-origination-svc",
             "trade-order-svc", "statements-svc", "check-capture-svc", "secrets-vault", "config-service",
             "dns-service", "load-balancer-mgmt", "alert-router", "token-service", "key-management-svc"],
)
# Lookalikes that make the real one harder to spot: expiring soon, but fine or minor.
DECOY_CERTS = [  # name, expires_on, auto_renew, team, used_by
    ("api-gateway.external", "2026-10-12", True, "Cloud Platform", ["api-gateway", "waf-gateway", "mobile-bff", "web-bff"]),
    ("sso.idp.signing", "2026-10-19", True, "Identity & Access", ["sso-federation-svc", "token-service", "auth-gateway"]),
    ("acquiring.mtls", "2026-10-27", True, "Merchant Services", ["acquiring-gateway", "settlement-svc", "terminal-mgmt-svc"]),
    ("branch-wifi.radius", "2026-10-14", False, "Branch & ATM Tech", ["branch-queue-svc", "appointment-svc"]),
]
# The last time it expired.
EGG_INCIDENT = dict(
    id="INC-0990", at="2025-10-10T03:12:00Z", sev=1, title="Internal TLS failures across the estate",
    cert="wildcard.internal.bank", affected=["api-gateway", "service-mesh", "auth-gateway", "payment-orchestrator",
                                              "card-auth-svc", "ledger-svc"],
    teams=["Cloud Platform", "Payments Platform", "Core Banking", "Cards"], minutes=240, impact="outage",
    customers=410_000, reassignments=3, detail="Certificate expired at 03:00 on a Friday; renewed by hand the same morning")
