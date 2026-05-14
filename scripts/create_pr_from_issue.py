#!/usr/bin/env python3
"""
Crea un Pull Request a partir de un issue enviado mediante template.
Se ejecuta en el workflow create-pr-from-issue.yml.

Variables de entorno esperadas:
  GITHUB_TOKEN   - Token de GitHub con permisos de escritura
  ISSUE_BODY     - Cuerpo del issue (formateado por el template YAML)
  ISSUE_NUMBER   - Número del issue
  LABEL_NAME     - Label del issue (whitelist-request | blacklist-request | false-positive)
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

# Mapeo de labels a configuración de reglas
RULE_MAP = {
    "whitelist-request": {
        "file": "rules/whitelist.yaml",
        "root_key": "repositories",
    },
    "blacklist-request": {
        "file": "rules/blacklist.yaml",
        "root_key": "repositories",
    },
    "false-positive": {
        "file": "rules/false_positives.yaml",
        "root_key": "issues",
    },
}


def get_env_or_fail(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"::error::Missing required env var: {name}")
        sys.exit(1)
    return value


def parse_issue_body(body: str) -> dict:
    """Parsea el cuerpo de un issue generado por formulario YAML.

    El formato es:
    ### Nombre del Campo
    valor

    ### Siguiente Campo
    valor
    """
    data = {}
    current_field = None
    current_value: list[str] = []

    for line in body.splitlines():
        if line.startswith("### "):
            if current_field is not None:
                data[current_field] = "\n".join(current_value).strip()
            current_field = line.removeprefix("### ").strip()
            current_value = []
        elif current_field is not None:
            current_value.append(line)

    if current_field is not None:
        data[current_field] = "\n".join(current_value).strip()

    return data


def github_api(method: str, endpoint: str, token: str) -> dict:
    """Llama a la API REST de GitHub y devuelve el JSON parseado."""
    url = f"https://api.github.com{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "hacs-compatibility-auditor-rules")

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"::error::GitHub API error {e.code} for {endpoint}: {body}")
        sys.exit(1)


def repo_exists(full_name: str, token: str) -> bool:
    """Verifica si un repositorio existe en GitHub."""
    try:
        github_api("GET", f"/repos/{full_name}", token)
        return True
    except SystemExit:
        return False


def load_yaml(filepath: Path) -> dict:
    """Carga un archivo YAML o devuelve dict vacío si no existe."""
    if not filepath.exists():
        return {}
    with open(filepath, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def is_duplicate_entry(filepath: Path, new_entry: dict, rule_type: str) -> bool:
    """Comprueba si una entrada ya existe en el archivo de reglas."""
    data = load_yaml(filepath)
    root_key = RULE_MAP[rule_type]["root_key"]
    entries = data.get(root_key, [])

    for entry in entries:
        if rule_type == "false-positive":
            if (entry.get("full_name") == new_entry.get("full_name") and
                    entry.get("issue_number") == new_entry.get("issue_number")):
                return True
        else:
            if entry.get("full_name") == new_entry.get("full_name"):
                return True
    return False


def append_entry(filepath: Path, entry: dict, rule_type: str):
    """Añade una entrada al archivo de reglas."""
    data = load_yaml(filepath)
    root_key = RULE_MAP[rule_type]["root_key"]
    if root_key not in data:
        data[root_key] = []
    data[root_key].append(entry)

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True, indent=2)


def main():
    token = get_env_or_fail("GITHUB_TOKEN")
    issue_body = get_env_or_fail("ISSUE_BODY")
    issue_number = get_env_or_fail("ISSUE_NUMBER")
    label_name = get_env_or_fail("LABEL_NAME")
    repo_full = os.environ.get("GITHUB_REPOSITORY", "")

    rule_cfg = RULE_MAP.get(label_name)
    if rule_cfg is None:
        print(f"::error::Unknown label: {label_name}")
        sys.exit(1)

    rule_file = Path(rule_cfg["file"])
    parsed = parse_issue_body(issue_body)
    issue_url = f"https://github.com/{repo_full}/issues/{issue_number}"

    # Extraer campos comunes
    full_name = parsed.get("Repositorio", "").strip()
    if not full_name or "/" not in full_name:
        print("::error::Formato de repositorio inválido. Debe ser owner/repo")
        sys.exit(1)

    if not repo_exists(full_name, token):
        print(f"::error::El repositorio {full_name} no existe en GitHub")
        sys.exit(1)

    reason = parsed.get("Motivo", "").strip()
    if not reason:
        print("::error::El motivo es obligatorio")
        sys.exit(1)

    # Construir entrada según el tipo
    if label_name in ("whitelist-request", "blacklist-request"):
        ha_version = parsed.get("Versión de Home Assistant", "").strip() or "*"
        entry = {
            "full_name": full_name,
            "reason": reason,
            "ha_version": ha_version,
            "added": "",
            "issue": issue_url,
        }
    else:
        issue_num_raw = parsed.get("Número de Issue", "").strip()
        if not issue_num_raw:
            print("::error::El número de issue es obligatorio")
            sys.exit(1)
        try:
            issue_num = int(issue_num_raw)
        except ValueError:
            print(f"::error::Número de issue inválido: {issue_num_raw}")
            sys.exit(1)

        # Verificar que la issue existe
        try:
            github_api("GET", f"/repos/{full_name}/issues/{issue_num}", token)
        except SystemExit:
            print(f"::error::La issue #{issue_num} no existe en {full_name}")
            sys.exit(1)

        entry = {
            "full_name": full_name,
            "issue_number": issue_num,
            "reason": reason,
            "added": "",
            "issue": issue_url,
        }

    # Verificar duplicados
    if is_duplicate_entry(rule_file, entry, label_name):
        print(f"::error::La entrada ya existe en {rule_file}")
        sys.exit(1)

    # Añadir entrada al archivo
    append_entry(rule_file, entry, label_name)

    # Outputs para el workflow
    branch = f"rules/{label_name}-{issue_number}"
    print(f"BRANCH={branch}")
    print(f"FILE={rule_cfg['file']}")

    # GitHub Actions output
    with open(os.environ.get("GITHUB_OUTPUT", "NUL"), "a" if "GITHUB_OUTPUT" in os.environ else "w") as f:
        print(f"branch={branch}", file=f)
        print(f"file={rule_cfg['file']}", file=f)

    print(f"[OK] Entrada creada para {full_name} en {rule_cfg['file']}")
    print(f"[OK] Rama: {branch}")


if __name__ == "__main__":
    main()
