"""
Service d'analyse statique du code.
Lance Ruff (linter) et Bandit (sécurité) sur un dossier de code Python via subprocess.
"""
import subprocess
import json
from pathlib import Path


def run_ruff(code_path: Path) -> dict:
    """Lance Ruff en mode JSON. Renvoie un dict {issues_count, issues, raw_output}."""
    try:
        result = subprocess.run(
            ["ruff", "check", str(code_path), "--output-format=json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Ruff retourne 0 si pas d'issue, 1 si issues détectées (les deux sont OK)
        try:
            issues = json.loads(result.stdout) if result.stdout.strip() else []
        except json.JSONDecodeError:
            issues = []

        return {
            "issues_count": len(issues),
            "issues": issues[:20],  # on cap à 20 pour l'affichage
            "raw_output": result.stdout[:5000],
        }
    except subprocess.TimeoutExpired:
        return {"issues_count": 0, "issues": [], "raw_output": "Timeout (60s)"}
    except Exception as e:
        return {"issues_count": 0, "issues": [], "raw_output": f"Erreur: {e}"}


def run_bandit(code_path: Path) -> dict:
    """Lance Bandit en mode JSON. Renvoie un dict {issues_count, issues, raw_output}."""
    try:
        result = subprocess.run(
            ["bandit", "-r", str(code_path), "-f", "json", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        try:
            data = json.loads(result.stdout) if result.stdout.strip() else {}
            issues = data.get("results", [])
        except json.JSONDecodeError:
            issues = []

        return {
            "issues_count": len(issues),
            "issues": issues[:20],
            "raw_output": result.stdout[:5000],
        }
    except subprocess.TimeoutExpired:
        return {"issues_count": 0, "issues": [], "raw_output": "Timeout (60s)"}
    except Exception as e:
        return {"issues_count": 0, "issues": [], "raw_output": f"Erreur: {e}"}


def format_ruff_summary(report: dict) -> str:
    """Format texte court pour affichage dans la step output."""
    n = report["issues_count"]
    if n == 0:
        return "✓ Aucune issue détectée par Ruff."
    lines = [f"⚠ {n} issue(s) détectée(s) par Ruff :", ""]
    for issue in report["issues"][:10]:
        code = issue.get("code", "?")
        msg = issue.get("message", "")
        loc = issue.get("location", {})
        file = loc.get("file", "?").split("/")[-1] if loc.get("file") else "?"
        line = loc.get("row", "?")
        lines.append(f"  [{code}] {file}:{line} — {msg}")
    return "\n".join(lines)


def format_bandit_summary(report: dict) -> str:
    n = report["issues_count"]
    if n == 0:
        return "✓ Aucune vulnérabilité détectée par Bandit."
    lines = [f"⚠ {n} problème(s) de sécurité détecté(s) par Bandit :", ""]
    for issue in report["issues"][:10]:
        test_id = issue.get("test_id", "?")
        severity = issue.get("issue_severity", "?")
        msg = issue.get("issue_text", "")
        file = issue.get("filename", "?").split("/")[-1]
        line = issue.get("line_number", "?")
        lines.append(f"  [{test_id}/{severity}] {file}:{line} — {msg}")
    return "\n".join(lines)