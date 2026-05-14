# HACS Compatibility Auditor Rules

Repositorio de reglas comunitarias para [HACS Compatibility Auditor](https://github.com/RmG152/hacs-compatibility-auditor).

## ¿Qué es esto?

La integración HACS Compatibility Auditor analiza repositorios HACS buscando posibles incompatibilidades con Home Assistant. Sin embargo, a veces puede generar **falsos positivos** (marcar como incompatible algo que funciona) o **falsos negativos** (no detectar una incompatibilidad real).

Este repositorio centraliza **reglas comunitarias revisadas** que la integración consume para mejorar su precisión:

| Regla | Propósito |
|-------|-----------|
| **Whitelist** | Repos que el algoritmo marca erróneamente pero son compatibles |
| **Blacklist** | Repos incompatibles que el algoritmo no detecta por sí solo |
| **False Positives** | Issues específicas que deben ignorarse en el análisis |
| **Label Overrides** | Ajustar pesos de labels por repositorio |
| **Keyword Overrides** | Ajustar pesos de keywords por repositorio |

## Cómo contribuir

Abre un issue usando la plantilla correspondiente:

- [Sugerir Whitelist](https://github.com/RmG152/hacs-compatibility-auditor-rules/issues/new?template=whitelist_request.yml) — para reportar un falso positivo
- [Sugerir Blacklist](https://github.com/RmG152/hacs-compatibility-auditor-rules/issues/new?template=blacklist_request.yml) — para reportar una incompatibilidad no detectada
- [Reportar Falso Positivo](https://github.com/RmG152/hacs-compatibility-auditor-rules/issues/new?template=false_positive_report.yml) — para ignorar una issue específica

Un workflow revisará automáticamente tu solicitud y creará un Pull Request. Un mantenedor revisará y aprobará los cambios.

## Estructura

```
rules/
├── whitelist.yaml            # Repos compatibles (anulan falsos positivos)
├── blacklist.yaml            # Repos incompatibles (anulan falsos negativos)
├── false_positives.yaml      # Issues específicas a ignorar
├── label_overrides.yaml      # Override de pesos de labels
└── keyword_overrides.yaml    # Override de pesos de keywords
index.json                    # Manifiesto generado automáticamente
```

## Formato de las reglas

### Whitelist / Blacklist

```yaml
repositories:
  - full_name: "owner/repo"
    reason: "Motivo de la inclusión"
    ha_version: ">=2026.1.0"    # Opcional, "*" = todas
    added: "2026-05-14"
    issue: "https://github.com/.../issues/1"
```

### False Positives

```yaml
issues:
  - full_name: "owner/repo"
    issue_number: 123
    reason: "Issue resuelta pero label no se limpió"
    added: "2026-05-14"
    issue: "https://github.com/.../issues/2"
```

### Label / Keyword Overrides

```yaml
overrides:
  - full_name: "owner/repo"
    labels:
      "breaking": 0         # Ignorar este label
      "incompatible": 5     # Reducir peso
```

## Licencia

MIT
