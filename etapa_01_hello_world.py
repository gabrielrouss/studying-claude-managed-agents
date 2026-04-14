"""
Etapa 1: Hello World - Primeiro Agent e Session
================================================

CONCEITOS APRENDIDOS:
- Agent: configuracao reutilizavel (modelo + system prompt + tools)
- Environment: container cloud onde o agente executa
- Session: instancia do agente rodando uma tarefa especifica
- Events/SSE: comunicacao bidirecional em tempo real
- Streaming: processar eventos conforme chegam

FLUXO:
1. Criar um Agent (define QUEM o agente e e O QUE ele pode fazer)
2. Criar um Environment (define ONDE ele roda)
3. Criar uma Session (junta agent + environment e INICIA o trabalho)
4. Enviar mensagem e processar stream de eventos

REQUISITOS:
- export ANTHROPIC_API_KEY="sua-chave-aqui"
- pip install anthropic>=0.52.0
"""

from anthropic import Anthropic


def main():
    # =========================================================================
    # PASSO 1: Instanciar o cliente
    # =========================================================================
    # O SDK le automaticamente a variavel de ambiente ANTHROPIC_API_KEY.
    # Ele tambem configura automaticamente o header beta necessario para
    # Managed Agents (managed-agents-2026-04-01).
    client = Anthropic()

    print("=" * 60)
    print("ETAPA 1: Hello World - Managed Agents")
    print("=" * 60)

    # =========================================================================
    # PASSO 2: Criar o Agent
    # =========================================================================
    # Um Agent e uma configuracao REUTILIZAVEL e VERSIONADA.
    # Voce cria uma vez e referencia por ID em quantas sessions quiser.
    #
    # Campos principais:
    # - name: nome legivel para humanos
    # - model: qual modelo Claude usar (sonnet, opus, haiku)
    # - system: system prompt que define personalidade/comportamento
    # - tools: quais ferramentas o agente pode usar
    #
    # O tipo "agent_toolset_20260401" habilita TODAS as tools built-in:
    # bash, read, write, edit, glob, grep, web_fetch, web_search
    print("\n[1/4] Criando Agent...")
    agent = client.beta.agents.create(
        name="Marketing Assistant - Hello World",
        model="claude-sonnet-4-6",
        system=(
            "Voce e um assistente de marketing criativo e direto. "
            "Responda sempre em portugues brasileiro. "
            "Quando solicitado, crie conteudo e salve em arquivos."
        ),
        tools=[
            {"type": "agent_toolset_20260401"},
        ],
    )
    print(f"    Agent criado!")
    print(f"    ID:      {agent.id}")
    print(f"    Version: {agent.version}")
    print(f"    Model:   {agent.model}")

    # =========================================================================
    # PASSO 3: Criar o Environment
    # =========================================================================
    # Um Environment define o CONTAINER CLOUD onde o agente executa.
    # Cada session recebe seu proprio container isolado, mesmo que
    # compartilhem o mesmo environment.
    #
    # Opcoes de networking:
    # - "unrestricted": acesso total a internet (exceto blocklist de seguranca)
    # - "limited": apenas hosts especificos na lista allowed_hosts
    #
    # O environment persiste ate ser arquivado ou deletado.
    print("\n[2/4] Criando Environment...")
    environment = client.beta.environments.create(
        name="hello-world-env",
        config={
            "type": "cloud",
            "networking": {"type": "unrestricted"},
        },
    )
    print(f"    Environment criado!")
    print(f"    ID: {environment.id}")

    # =========================================================================
    # PASSO 4: Criar a Session
    # =========================================================================
    # Uma Session JUNTA um Agent + Environment e inicia a execucao.
    # A session tem:
    # - Filesystem persistente (durante a vida da session)
    # - Historico de conversacao mantido server-side
    # - Status: running, idle, terminated
    print("\n[3/4] Criando Session...")
    session = client.beta.sessions.create(
        agent=agent.id,
        environment_id=environment.id,
        title="Hello World - Primeiro teste",
    )
    print(f"    Session criada!")
    print(f"    ID:     {session.id}")
    print(f"    Status: {session.status}")

    # =========================================================================
    # PASSO 5: Enviar mensagem e processar stream
    # =========================================================================
    # A comunicacao e baseada em EVENTOS:
    #
    # Voce envia -> user.message (texto para o agente)
    # Voce recebe <- agent.message (resposta de texto)
    #                agent.tool_use (agente usando uma ferramenta)
    #                agent.tool_result (resultado da ferramenta)
    #                session.status_idle (agente terminou)
    #
    # O fluxo e:
    # 1. Abrir stream SSE (Server-Sent Events)
    # 2. Enviar mensagem do usuario
    # 3. Processar eventos conforme chegam em tempo real
    print("\n[4/4] Enviando mensagem e processando stream...")
    print("-" * 60)

    # Abrir o stream PRIMEIRO, depois enviar a mensagem
    with client.beta.sessions.events.stream(session.id) as stream:
        # Enviar mensagem do usuario
        client.beta.sessions.events.send(
            session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Crie um arquivo chamado hello.md com uma breve "
                                "mensagem de boas-vindas para um time de marketing "
                                "que esta comecando a usar IA. Maximo 5 linhas."
                            ),
                        },
                    ],
                },
            ],
        )

        # Processar eventos do stream
        for event in stream:
            match event.type:
                # Resposta de texto do agente
                case "agent.message":
                    for block in event.content:
                        if hasattr(block, "text"):
                            print(f"[AGENT] {block.text}")

                # Agente usando uma ferramenta (bash, write, read, etc.)
                case "agent.tool_use":
                    print(f"\n[TOOL]  Usando: {event.name}")
                    if hasattr(event, "input") and event.input:
                        # Mostrar preview do input (truncado)
                        input_str = str(event.input)
                        if len(input_str) > 200:
                            input_str = input_str[:200] + "..."
                        print(f"        Input: {input_str}")

                # Resultado de ferramenta
                case "agent.tool_result":
                    status = "OK" if not event.is_error else "ERRO"
                    print(f"[RESULT] {status}")

                # Agente ficou idle (terminou o trabalho)
                case "session.status_idle":
                    print("\n" + "-" * 60)
                    print("[SESSION] Agente terminou! Status: idle")
                    # stop_reason indica POR QUE o agente parou
                    if hasattr(event, "stop_reason") and event.stop_reason:
                        print(f"          Stop reason: {event.stop_reason.type}")
                    break

                # Agente esta processando
                case "session.status_running":
                    print("[SESSION] Agente processando...")

                # Eventos de modelo (observabilidade)
                case "span.model_request_start":
                    print("[SPAN]   Chamada ao modelo iniciada...")

                case "span.model_request_end":
                    if hasattr(event, "model_usage") and event.model_usage:
                        usage = event.model_usage
                        print(
                            f"[SPAN]   Modelo respondeu - "
                            f"Input: {usage.input_tokens} tokens, "
                            f"Output: {usage.output_tokens} tokens"
                        )

    # =========================================================================
    # CLEANUP: Limpar recursos criados
    # =========================================================================
    print("\n" + "=" * 60)
    print("CLEANUP")
    print("=" * 60)

    # Arquivar o agent (read-only, sessions existentes continuam)
    client.beta.agents.archive(agent.id)
    print(f"Agent {agent.id} arquivado")

    # Deletar o environment
    # Nota: so funciona se nenhuma session ativa referencia ele
    try:
        client.beta.environments.delete(environment.id)
        print(f"Environment {environment.id} deletado")
    except Exception as e:
        print(f"Environment nao pode ser deletado (sessions ativas?): {e}")

    print("\nEtapa 1 concluida com sucesso!")


if __name__ == "__main__":
    main()
