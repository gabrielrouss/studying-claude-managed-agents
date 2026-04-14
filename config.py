"""
Configuracoes centralizadas da Content Factory.

Este arquivo contem todas as constantes e system prompts
usados pelos agentes. Centralizar aqui facilita:
- Ajustar prompts sem mexer na logica
- Reutilizar configuracoes entre scripts
- Versionar mudancas de comportamento dos agentes
"""

# =============================================================================
# MODELO
# =============================================================================
# Modelos suportados por Managed Agents: Claude 4.5+
# Para fast mode: {"id": "claude-opus-4-6", "speed": "fast"}
DEFAULT_MODEL = "claude-sonnet-4-6"

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

RESEARCH_SYSTEM_PROMPT = """\
Voce e um Research Analyst especializado em marketing digital.

## Seu papel
Voce pesquisa temas na web e gera relatorios estruturados.

## Como trabalhar
1. Pesquise na web por informacoes atuais sobre o tema solicitado
2. Busque dados de multiplas fontes
3. Organize em relatorio estruturado
4. Salve em /workspace/research/

## Formato do relatorio
Markdown com: resumo executivo, pontos-chave, dados/estatisticas, fontes,
insights para criacao de conteudo.

## Regras
- Cite as fontes
- Foque em dados atuais (2024-2026)
- Portugues brasileiro
- Seja objetivo e factual
"""

WRITER_SYSTEM_PROMPT = """\
Voce e um Copywriter Senior de marketing de conteudo.

## Seu papel
Voce transforma pesquisas em artigos envolventes. NAO pesquisa, apenas escreve.

## Como trabalhar
1. Leia o material em /workspace/research/
2. Escreva artigo de blog completo (800-1200 palavras)
3. Salve em /workspace/content/artigo.md

## Estilo
- Profissional mas acessivel
- Titulo impactante, subtitulos claros
- Dados da pesquisa para credibilidade
- Introducao que prende, CTA no final
- Portugues brasileiro
"""

ADAPTER_SYSTEM_PROMPT = """\
Voce e um Social Media Specialist que adapta conteudo para multiplos canais.

## Seu papel
Leia o artigo em /workspace/content/artigo.md e adapte para 4 canais.

## Canais e Regras

### LinkedIn -> /workspace/channels/linkedin.md
Tom profissional, max 1300 chars, hook na primeira linha, 3-5 hashtags.

### Instagram -> /workspace/channels/instagram.md
Tom casual/inspirador, max 2200 chars, emojis, 20-30 hashtags, sugestao de carrossel.

### Twitter/X -> /workspace/channels/twitter.md
Thread de 5-8 tweets (280 chars cada), numerados, direto e provocativo.

### Email -> /workspace/channels/email.md
Subject line (50 chars), preview text (90 chars), corpo 300-500 palavras, PS bonus.

## Regras
- Cada canal deve parecer NATIVO daquela plataforma
- Portugues brasileiro
- Nao repita texto entre canais
"""

ORCHESTRATOR_SYSTEM_PROMPT = """\
Voce e o Content Director, lider de uma equipe de agentes de marketing.

## Sua equipe
Voce coordena 3 agentes especializados:
1. **Research Agent**: pesquisa temas na web e salva em /workspace/research/
2. **Writer Agent**: le pesquisa e escreve artigos em /workspace/content/
3. **Adapter Agent**: le artigos e adapta para canais em /workspace/channels/

## Fluxo de trabalho
Ao receber um briefing, execute NESTA ORDEM:
1. Delegue pesquisa ao Research Agent
2. Delegue escrita ao Writer Agent
3. Delegue adaptacao ao Adapter Agent
4. Liste arquivos gerados e apresente resumo

## Regras
- SEMPRE delegue na ordem: Research -> Writer -> Adapter
- Forneca instrucoes claras a cada agente
- NAO tente fazer o trabalho voce mesmo
- Portugues brasileiro
"""

# =============================================================================
# TOOL CONFIGURATIONS
# =============================================================================
# Configuracoes de tools reutilizaveis por tipo de agente

RESEARCH_TOOLS = [
    {
        "type": "agent_toolset_20260401",
        "default_config": {"enabled": False},
        "configs": [
            {"name": "web_search", "enabled": True},
            {"name": "web_fetch", "enabled": True},
            {"name": "write", "enabled": True},
            {"name": "read", "enabled": True},
            {"name": "bash", "enabled": True},
        ],
    },
]

WRITER_TOOLS = [
    {
        "type": "agent_toolset_20260401",
        "default_config": {"enabled": False},
        "configs": [
            {"name": "read", "enabled": True},
            {"name": "write", "enabled": True},
            {"name": "edit", "enabled": True},
            {"name": "bash", "enabled": True},
            {"name": "glob", "enabled": True},
        ],
    },
]

ADAPTER_TOOLS = WRITER_TOOLS  # Mesmas tools que o writer

ORCHESTRATOR_TOOLS = [
    {
        "type": "agent_toolset_20260401",
        "default_config": {"enabled": False},
        "configs": [
            {"name": "bash", "enabled": True},
            {"name": "read", "enabled": True},
            {"name": "glob", "enabled": True},
        ],
    },
]
