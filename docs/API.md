i2Sales API – Guia de Integração (Frontend)

Base URL
- Local: `http://localhost:5000/api/v1`
- Produção (Render): defina `BASE_URL = https://i2sales-be-test.onrender.com/api/v1`

Como usar nos serviços do frontend
- Construa URLs como `${BASE_URL}/auth/login`, `${BASE_URL}/clients`, etc.
- Header padrão: `Authorization: Bearer <JWT>` (todas as rotas protegidas)

Autenticação
- `POST ${BASE_URL}/auth/login`
  - Request: `{ "email": "admin@x.com", "password": "1234567890" }`
  - Response: `{ "token": "...", "user": { "id", "name", "email", "role" } }`
- `GET ${BASE_URL}/auth/me` → `{ "id", "name", "email", "role" }`

Erros
- Formato: `{ "error": "Mensagem...", "detail"?: "..." }`
- Códigos: 400, 401, 403, 404, 500

Clientes
- `POST ${BASE_URL}/clients`
  - Body: `{ name, phone, source, status?, followUpState?, email?, observations?, product?, propertyValue? }`
  - Defaults: `status="Primeiro Atendimento"`, `followUpState="Sem Follow Up"`
  - Efeito: cria Interaction `CLIENT_CREATED`
- `GET ${BASE_URL}/clients?q=<texto>`
  - Lista (máx. 200), ordenada por `updatedAt desc`
- `GET ${BASE_URL}/clients/{id}`
  - Inclui `interactions` ordenadas por `createdAt desc`
- `PUT ${BASE_URL}/clients/{id}`
  - Campos: `name, phone, email, observations, product, propertyValue, status, followUpState`
  - Validações: status e followUpState aceitam `Concluído/Concluido` (normaliza para `Concluido`)
- `DELETE ${BASE_URL}/clients/{id}` (ADMIN)
  - 204 No Content
- `GET ${BASE_URL}/clients/export`
  - `text/csv` com cabeçalho `id,name,phone,email,source,status,followUpState,product,propertyValue,createdAt,updatedAt`

Interações
- `POST ${BASE_URL}/interactions`
  - Body: `{ clientId, type, observation?, explicitNext? }`
  - Sem `type` e com `observation` → assume `NOTE`; `OBSERVATION` tratado como `NOTE`
  - Efeitos:
    - `STATUS_CHANGE` + `explicitNext`: altera `client.status`
    - `FOLLOW_UP_SCHEDULED`: `client.followUpState = "Ativo"`
    - `FOLLOW_UP_*` (DONE/CANCELED/CANCELLED/LOST/CLOSED): `client.followUpState = "Sem Follow Up"`
    - `NOTE`: sem efeito em cliente
  - Response: 201

Analytics
- `GET ${BASE_URL}/analytics/broker-kpis`
  - `{ followUpAtrasado, leadsEmTratativa, leadsPrimeiroAtendimento, totalLeads }`
- `GET ${BASE_URL}/analytics/productivity?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&brokerId?=`
  - `{ series: [ { date, count } ] }`
- `GET ${BASE_URL}/analytics/funnel?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&brokerId?=`
  - `{ stages: { "Primeiro Atendimento": n, "Em Tratativa": n, "Proposta": n, "Fechado": n } }`

Health
- `GET ${BASE_URL}/health` → `{ "status": "ok" }`

RBAC
- `BROKER`: vê somente `owner_id == sub`
- `MANAGER`/`ADMIN`: vê tudo; `ADMIN` requerido para deletar clientes
