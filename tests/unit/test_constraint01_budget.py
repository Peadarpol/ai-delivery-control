import pytest
from src.scripts.ai_review import load_review_context

def test_budget_baseline_commit():
    plain_diff = """diff --git a/src/main.py b/src/main.py
index 1234567..89abcde 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,4 @@
 def main():
-    pass
+    print("hello world")
"""
    context = load_review_context(plain_diff)
    est_tokens = len(context) // 4
    total_budget = est_tokens + 600 + 400
    print(f"\n[BUDGET] Baseline estimated tokens: {est_tokens}")
    print(f"[BUDGET] Baseline total budget (with caps): {total_budget}")
    assert total_budget < 2000, f"Baseline total budget {total_budget} exceeds 2000 limit"


def test_budget_adr_commit():
    adr_diff = """diff --git a/docs/adr/0001.md b/docs/adr/0001.md
index 1234567..89abcde 100644
--- a/docs/adr/0001.md
+++ b/docs/adr/0001.md
@@ -1,3 +1,8 @@
+# ADR: Test Decision
+Decision /
+Tradeoff: AT1
+Exposes: FM1
+Mitigation: None
"""
    context = load_review_context(adr_diff)
    est_tokens = len(context) // 4
    total_budget = est_tokens + 600 + 400
    print(f"\n[BUDGET] ADR estimated tokens: {est_tokens}")
    print(f"[BUDGET] ADR total budget (with caps): {total_budget}")
    assert total_budget < 2000, f"ADR total budget {total_budget} exceeds 2000 limit"
