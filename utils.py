"""
Etapa 6: Utils - Funcoes auxiliares reutilizaveis
==================================================

CONCEITOS APRENDIDOS:
- Lifecycle management: listar, arquivar e deletar recursos
- Reutilizacao de agents e environments entre sessions
- Helper generico para processar stream de eventos
- Pattern para cleanup de recursos

Estas funcoes sao usadas para:
- Evitar criar agents/environments duplicados
- Processar streams de forma padronizada
- Limpar recursos ao final dos testes
"""

from anthropic import Anthropic


def get_client() -> Anthropic:
    """Retorna cliente Anthropic configurado."""
    return Anthropic()


# =============================================================================
# AGENT HELPERS
# =============================================================================


def find_agent_by_name(client: Anthropic, name: str):
    """
    Busca um agent existente pelo nome.

    Util para evitar criar duplicatas durante desenvolvimento.
    Retorna o agent se encontrado, None caso contrario.

    NOTA: A API lista agents paginados. Em producao com muitos agents,
    voce deveria armazenar IDs em um banco de dados em vez de buscar por nome.
    """
    # Iterar o objeto paginado diretamente (nao .data) para percorrer todas as paginas
    for agent in client.beta.agents.list():
        if agent.name == name and agent.archived_at is None:
            return agent
    return None


def create_or_get_agent(client: Anthropic, **kwargs):
    """
    Cria um agent ou retorna um existente com o mesmo nome.

    Parametros sao os mesmos de client.beta.agents.create():
    - name, model, system, tools, callable_agents, etc.
    """
    name = kwargs.get("name", "")
    existing = find_agent_by_name(client, name)
    if existing:
        print(f"    Agent '{name}' ja existe: {existing.id} (v{existing.version})")
        return existing

    agent = client.beta.agents.create(**kwargs)
    print(f"    Agent '{name}' criado: {agent.id} (v{agent.version})")
    return agent


# =============================================================================
# ENVIRONMENT HELPERS
# =============================================================================


def find_environment_by_name(client: Anthropic, name: str):
    """
    Busca um environment existente pelo nome.

    Environments devem ter nome unico na organizacao/workspace.
    """
    # Iterar o objeto paginado diretamente (nao .data) para percorrer todas as paginas
    for env in client.beta.environments.list():
        if env.name == name and env.archived_at is None:
            return env
    return None


def create_or_get_environment(client: Anthropic, **kwargs):
    """
    Cria um environment ou retorna um existente com o mesmo nome.

    Parametros sao os mesmos de client.beta.environments.create():
    - name, config (type, networking, packages)
    """
    name = kwargs.get("name", "")
    existing = find_environment_by_name(client, name)
    if existing:
        print(f"    Environment '{name}' ja existe: {existing.id}")
        return existing

    env = client.beta.environments.create(**kwargs)
    print(f"    Environment '{name}' criado: {env.id}")
    return env


# =============================================================================
# STREAM HELPERS
# =============================================================================


def stream_session(client: Anthropic, session_id: str, message: str):
    """
    Envia uma mensagem e processa o stream de eventos de forma padronizada.

    Imprime eventos formatados no terminal e retorna estatisticas.

    Retorna dict com:
    - tool_count: numero total de tool calls
    - threads: dict de thread_id -> agent_name (se multi-agent)
    """
    stats = {"tool_count": 0, "threads": {}}

    with client.beta.sessions.events.stream(session_id) as stream:
        client.beta.sessions.events.send(
            session_id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": message}],
                },
            ],
        )

        for event in stream:
            match event.type:
                # --- Agent events ---
                case "agent.message":
                    for block in event.content:
                        if hasattr(block, "text"):
                            print(f"[AGENT] {block.text}")

                case "agent.tool_use":
                    stats["tool_count"] += 1
                    print(f"[TOOL]  {event.name}")

                case "agent.tool_result":
                    status = "OK" if not event.is_error else "ERRO"
                    print(f"        -> {status}")

                # --- Multi-agent events ---
                case "session.thread_created":
                    tid = getattr(event, "session_thread_id", "?")
                    name = getattr(event, "agent_name", "Unknown")
                    stats["threads"][tid] = name
                    print(f"[THREAD] {name} iniciou")

                case "session.thread_idle":
                    tid = getattr(event, "session_thread_id", "?")
                    name = stats["threads"].get(tid, "Unknown")
                    print(f"[THREAD] {name} terminou")

                # --- Session events ---
                case "session.status_idle":
                    print(f"\n[DONE] Session idle ({stats['tool_count']} tools)")
                    break

                # --- Usage ---
                case "span.model_request_end":
                    if hasattr(event, "model_usage") and event.model_usage:
                        u = event.model_usage
                        print(f"[USAGE] In:{u.input_tokens} Out:{u.output_tokens}")

    return stats


# =============================================================================
# CLEANUP HELPERS
# =============================================================================


def cleanup_agents(client: Anthropic, agents: list):
    """
    Arquiva uma lista de agents.

    Agents arquivados ficam read-only. Sessions existentes continuam
    rodando, mas novas sessions nao podem referencia-los.
    """
    for agent in agents:
        try:
            client.beta.agents.archive(agent.id)
            print(f"  Archived: {agent.name} ({agent.id})")
        except Exception as e:
            print(f"  Erro ao arquivar {agent.name}: {e}")


def cleanup_environments(client: Anthropic, environments: list):
    """
    Deleta uma lista de environments.

    So funciona se nenhuma session ativa referencia o environment.
    Se falhar, tenta arquivar em vez de deletar.
    """
    for env in environments:
        try:
            client.beta.environments.delete(env.id)
            print(f"  Deleted: {env.name} ({env.id})")
        except Exception:
            try:
                client.beta.environments.archive(env.id)
                print(f"  Archived (delete failed): {env.name} ({env.id})")
            except Exception as e:
                print(f"  Erro: {env.name}: {e}")


def cleanup_all(client: Anthropic, agents: list = None, environments: list = None):
    """Limpa todos os recursos fornecidos."""
    print("\n--- CLEANUP ---")
    if agents:
        cleanup_agents(client, agents)
    if environments:
        cleanup_environments(client, environments)
    print("--- CLEANUP COMPLETO ---\n")


# =============================================================================
# LIST HELPERS
# =============================================================================


def list_all_agents(client: Anthropic):
    """Lista todos os agents da organizacao."""
    print("\n--- AGENTS ---")
    count = 0
    for agent in client.beta.agents.list():
        status = "ARCHIVED" if agent.archived_at else "ACTIVE"
        print(f"  [{status}] {agent.name} ({agent.id}, v{agent.version})")
        count += 1
    print(f"  Total: {count}")


def list_all_environments(client: Anthropic):
    """Lista todos os environments da organizacao."""
    print("\n--- ENVIRONMENTS ---")
    count = 0
    for env in client.beta.environments.list():
        status = "ARCHIVED" if env.archived_at else "ACTIVE"
        print(f"  [{status}] {env.name} ({env.id})")
        count += 1
    print(f"  Total: {count}")
