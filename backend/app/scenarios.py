"""Sample failures with hidden ground truth. `knows` and `persona` stay on the server and drive simulated engineers."""

SCENARIOS = {
    "checkout-pool": {
        "title": "Production deploy failed: checkout-service never became healthy",
        "blurb": "A config change shrinks the database pool. Two people, one of whom only skimmed the diff.",
        "repo": "acme/checkout-service", "branch": "main", "commit_sha": "a3f9c21",
        "commit_message": "tune db settings for flaky staging", "workflow": "deploy-production",
        "logs": """2026-03-12T09:41:07Z deploy  Rolling out checkout-service@a3f9c21 to production (4 replicas)
2026-03-12T09:41:52Z deploy  replica-1 started, waiting for /healthz
2026-03-12T09:42:22Z app     INFO  Loaded config from config/db.yaml (pool_size=5, max_overflow=0)
2026-03-12T09:42:31Z app     ERROR sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 0 reached, connection timed out, timeout 30.00
2026-03-12T09:42:31Z app     WARN  /healthz degraded: db_pool_wait_ms=29984
2026-03-12T09:42:52Z deploy  replica-1 failed readiness probe (3/3)
2026-03-12T09:43:10Z app     ERROR POST /v1/checkout 503 upstream timeout
2026-03-12T09:43:55Z deploy  Rollout aborted: 1/4 replicas healthy, error budget exceeded
2026-03-12T09:43:56Z deploy  ERROR deployment "checkout-service" failed: progress deadline exceeded""",
        "diff": """diff --git a/config/db.yaml b/config/db.yaml
--- a/config/db.yaml
+++ b/config/db.yaml
@@ -3,7 +3,7 @@ database:
   host: ${DB_HOST}
-  pool_size: 20
-  max_overflow: 10
+  pool_size: 5
+  max_overflow: 0
   pool_timeout: 30
diff --git a/tests/test_pricing.py b/tests/test_pricing.py
--- a/tests/test_pricing.py
+++ b/tests/test_pricing.py
@@ -12,3 +12,5 @@ def test_discount():
     assert price(100, 0.1) == 90
+def test_zero_discount():
+    assert price(100, 0) == 100""",
        "participants": [
            {"name": "Priya Nair", "role": "Backend engineer, commit author", "handle": "@priya",
             "knows": "You copied the pool settings from the staging values file on Tuesday because staging kept hitting connection limits on its small database. You meant to put them in a staging override but edited the shared config/db.yaml. You did not load test. The PR was approved fast.",
             "persona": "Cooperative and a little embarrassed. Precise when asked something specific, never volunteers extra."},
            {"name": "Marcus Webb", "role": "Reviewer who approved the pull request", "handle": "@marcus",
             "knows": "You approved the PR. config/ is not covered by CODEOWNERS, so you were only asked to review the Python files. You skimmed the diff and do not remember seeing the db.yaml change.",
             "persona": "Defensive at first, saying the PR looked fine, then admits he mostly looked at the code and test files."},
        ],
    },
    "werkzeug-pin": {
        "title": "CI build failed: payments-api cannot import werkzeug.urls",
        "blurb": "A dependency cleanup removes a pin that masked an incompatibility. Other repos may be at risk.",
        "repo": "acme/payments-api", "branch": "main", "commit_sha": "7be41d0",
        "commit_message": "chore: clean up unused dependencies", "workflow": "ci-build",
        "logs": """Run pytest -q
==================================== ERRORS ====================================
_________________ ERROR collecting tests/test_webhooks.py ______________________
ImportError while importing test module 'tests/test_webhooks.py'.
tests/test_webhooks.py:3: in <module>
    from app.webhooks import verify_signature
app/webhooks.py:7: in <module>
    from werkzeug.urls import url_quote
E   ImportError: cannot import name 'url_quote' from 'werkzeug.urls'
Installed: Flask 2.2.5, Werkzeug 3.0.1
Error: Process completed with exit code 2.""",
        "diff": """diff --git a/requirements.txt b/requirements.txt
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,6 +1,4 @@
 flask==2.2.5
-werkzeug==2.2.3
-itsdangerous==2.1.2
 gunicorn==21.2.0
 stripe==8.4.0""",
        "participants": [
            {"name": "Tomás Rivera", "role": "Platform engineer, commit author", "handle": "@tomas",
             "knows": "On Friday you ran a dependency-pruning script across five repos to shrink images for a cost initiative. It flagged werkzeug as unused because no top-level module imports it directly, though app/webhooks.py imports werkzeug.urls. You tested locally in an old virtualenv that still had Werkzeug 2.2.3, so it passed.",
             "persona": "Cooperative and detail-oriented, but vague on exactly which repos the script touched."},
            {"name": "Aisha Khan", "role": "On-call SRE", "handle": "@aisha",
             "knows": "CI caches the pip layer keyed on a hash of requirements.txt, so this change invalidated the cache and exposed the new resolution. You noticed the same script changed other repos and have not checked them yet.",
             "persona": "Helpful, and tends to speculate beyond what she actually knows unless asked directly."},
        ],
    },
    "secret-rotation": {
        "title": "Deploy failed: payments-worker rejected after secret rotation",
        "blurb": "An engineer is sure every consumer was restarted. The logs disagree.",
        "repo": "acme/web-platform", "branch": "main", "commit_sha": "c19d8e4",
        "commit_message": "rotate auth-service client secret (SEC-412)", "workflow": "deploy-production",
        "logs": """2026-03-14T02:10:03Z deploy          Applying terraform plan: 1 to change (vault_generic_secret.auth_client)
2026-03-14T02:10:41Z deploy          Secret auth/client_secret updated to version 14
2026-03-14T02:11:20Z web-api         INFO  Fetched secret auth/client_secret version=14
2026-03-14T02:11:24Z payments-worker INFO  Using cached secret auth/client_secret version=13
2026-03-14T02:11:39Z auth-service    WARN  client=payments-worker invalid client secret (attempt 1)
2026-03-14T02:11:41Z auth-service    WARN  client=payments-worker invalid client secret (attempt 2)
2026-03-14T02:12:05Z payments-worker ERROR token exchange failed: 401 Unauthorized
2026-03-14T02:12:30Z deploy          Health check failed: payments-worker 0/3 ready
2026-03-14T02:12:31Z deploy          ERROR deployment "web-platform" failed: post-deploy verification failed""",
        "diff": """diff --git a/infra/vault.tf b/infra/vault.tf
--- a/infra/vault.tf
+++ b/infra/vault.tf
@@ -41,5 +41,5 @@ resource "vault_generic_secret" "auth_client" {
   data_json = jsonencode({
-    client_secret = var.auth_client_secret_v13
+    client_secret = var.auth_client_secret_v14
   })
 }""",
        "participants": [
            {"name": "Jonas Weber", "role": "Security engineer, ran the rotation", "handle": "@jonas",
             "knows": "You rotated the secret for SEC-412. Step 4 of the runbook says to restart every consumer. You restarted web-api and believe you restarted everything, but payments-worker runs in a separate cluster and is missing from the runbook's consumer list.",
             "persona": "Confident and slightly mistaken. Insists all consumers were restarted until shown the payments-worker log line, then concedes the runbook list is outdated."},
            {"name": "Lena Park", "role": "Payments engineer", "handle": "@lena",
             "knows": "payments-worker caches secrets for 24 hours and refreshes only on restart. Nobody told your team about the rotation; you found out when alerts fired. The runbook's consumer list predates payments-worker moving to the new cluster.",
             "persona": "Calm and factual."},
        ],
    },
}


def public_list() -> list[dict]:
    return [{"key": k, "title": v["title"], "repo": v["repo"], "blurb": v["blurb"], "people": len(v["participants"])}
            for k, v in SCENARIOS.items()]


def persona_for(key: str | None, name: str) -> tuple[str, str]:
    for p in SCENARIOS.get(key or "", {}).get("participants", []):
        if p["name"] == name:
            return p["knows"], p["persona"]
    return "You have limited knowledge of this failure.", "Cooperative and brief."
