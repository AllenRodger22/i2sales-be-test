i2Sales API – Guia de Integração (Frontend)

Base URL
- Local: `http://localhost:5000/api/v1`
- Produção (Render): `https://<seu-servico>.onrender.com/api/v1`

Autenticação
- Header: `Authorization: Bearer <JWT>` (em todas as rotas protegidas)
- Login: `POST /auth/login`
  - Request JSON: `{ "email": "admin@x.com", "password": "1234567890" }`
  - Response: `{ "token": "...", "user": { "id", "name", "email", "role" } }`
- Sessão: `GET /auth/me` → `{ "id", "name", "email", "role" }`

Erros
- Formato: `{ "error": "Mensagem...", "detail"?: "..." }`
- Códigos: `400` (input inválido), `401` (auth), `403` (RBAC), `404` (não encontrado), `500` (erro interno)

Clientes (`/clients`)
- Criar: `POST /clients`
  - Body: `{ name, phone, source, status?, followUpState?, email?, observations?, product?, propertyValue? }`
  - Defaults: `status="Primeiro Atendimento"`, `followUpState="Sem Follow Up"`
  - Response 201: objeto do cliente (camelCase), sem interactions embutidas
  - Efeito: cria uma Interaction `CLIENT_CREATED`
- Listar: `GET /clients?q=<texto>`
  - Retorna lista (máx. 200), ordenada por `updatedAt` desc
  - Filtro `q`: faz ilike em `name`, `phone`, `email`, `source`
- Detalhe: `GET /clients/{id}`
  - Inclui `interactions` ordenadas por `createdAt` desc
- Atualizar: `PUT /clients/{id}`
  - Campos aceitos: `name, phone, email, observations, product, propertyValue, status, followUpState`
  - Validações:
    - `status` permitido: `Primeiro Atendimento, Em Tratativa, Proposta, Fechado, Ativo, Atrasado, Concluído/Concluido, Cancelado, Perdido`
    - `followUpState` permitido: `Sem Follow Up, Ativo, Atrasado, Concluído/Concluido, Cancelado, Perdido`
    - Observação: a API normaliza `Concluído` → `Concluido` ao salvar
- Excluir: `DELETE /clients/{id}` (ADMIN)
  - Response: `204 No Content`
- Exportar CSV: `GET /clients/export`
  - Response: `text/csv` com cabeçalho `id,name,phone,email,source,status,followUpState,product,propertyValue,createdAt,updatedAt`

Interações (`/interactions`)
- Criar: `POST /interactions`
  - Body base: `{ clientId: UUID, type: string, observation?: string, explicitNext?: string }`
  - Alias: se `type` ausente e `observation` presente, assume `type="NOTE"`; `OBSERVATION` é tratado como `NOTE`
  - Side-effects por tipo:
    - `STATUS_CHANGE` + `explicitNext`: atualiza `client.status = explicitNext`
    - `FOLLOW_UP_SCHEDULED`: `client.followUpState = "Ativo"`
    - `FOLLOW_UP_DONE/CANCELED/CANCELLED/LOST/CLOSED`: `client.followUpState = "Sem Follow Up"`
    - `NOTE`: sem efeitos em cliente
  - Response 201: `{ "message": "Interação criada com sucesso." }`

Analytics (`/analytics`)
- Broker KPIs: `GET /analytics/broker-kpis`
  - Retorna: `{ followUpAtrasado, leadsEmTratativa, leadsPrimeiroAtendimento, totalLeads }`
  - RBAC: se `role=BROKER`, filtra por `owner_id = sub`
- Produtividade: `GET /analytics/productivity?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&brokerId?=`
  - Series por dia: `{ series: [ { date: YYYY-MM-DD, count: number } ] }`
  - RBAC: `BROKER` força `brokerId = sub`
- Funil: `GET /analytics/funnel?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&brokerId?=`
  - Retorna: `{ stages: { "Primeiro Atendimento": n, "Em Tratativa": n, "Proposta": n, "Fechado": n } }`
  - RBAC: `BROKER` força filtro por `owner_id = sub`

Health
- `GET /health` → `{ "status": "ok" }`

Notas de RBAC
- `BROKER`: vê apenas clientes onde `owner_id == sub` (JWT)
- `MANAGER`/`ADMIN`: visualizam tudo
- `ADMIN`: necessário para `DELETE /clients/{id}`

Boas práticas no frontend
- Sempre enviar `Authorization: Bearer <token>`
- Tratar `401` limpando o token e redirecionando ao login
- Para uploads/downloads, usar `apiClient` com `Blob`/`FormData` conforme necessário (CSV de export já é `text/csv`)
