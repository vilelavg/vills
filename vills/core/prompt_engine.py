"""PromptEngine — compõe prompts dinâmicos por tenant, segmento e tom."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from vills.tenancy.context import TenantContext

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class PromptTemplateNotFoundError(Exception):
    """Template de prompt não existe."""


class PromptEngine:
    def __init__(self, templates_dir: Path | None = None) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir or PROMPTS_DIR)),
            autoescape=select_autoescape(enabled_extensions=()),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(
        self,
        template_name: str,
        tenant: TenantContext,
        **extra_vars: Any,
    ) -> str:
        """Renderiza um prompt com o contexto do tenant + variáveis extras."""
        try:
            template = self._env.get_template(f"{template_name}.j2")
        except Exception as exc:
            raise PromptTemplateNotFoundError(
                f"Template '{template_name}' não encontrado"
            ) from exc

        config = tenant.merged_config()
        context_vars = {
            "agency_name": tenant.agency_slug,
            "scope": tenant.scope_label,
            "is_client_scope": tenant.is_client_scope,
            "segment": tenant.client_segment or "generico",
            "tone": config.get("tone", "profissional e cordial"),
            "language": config.get("language", "pt-BR"),
            **extra_vars,
        }
        return template.render(**context_vars).strip()
