i2Sales API - Guia de Integração

Base URL
- Local: `http://localhost:5000/api/v1`
- Produção: `https://i2sales-be-test.onrender.com/api/v1`

Headers Padrão
- Protegidas: `Authorization: Bearer <Supabase Access Token>`
- CORS: preflight `OPTIONS` em `/api/v1/*` responde 204 e não exige JWT.

Autenticação (Supabase)
- Fluxo: o frontend autentica via Supabase e envia o `access_token` nas requisições ao backend.
- Variável de ambiente obrigatória no backend: `SUPABASE_JWT_SECRET` (de Supabase → Settings → API → JWT Secret).
- Endpoints legados descontinuados:
  - `POST /auth/register` → 410 (não usar; cadastro é no Supabase)
  - `POST /auth/login` → 410 (não usar; login é no Supabase)
- GET `${BASE_URL}/auth/me`
  - Protegido por Supabase JWT (audience `authenticated`)
  - 200 → `{ id, name, email, role }`

Clientes
- POST `${BASE_URL}/clients`
  - Body: `{ name, phone, source, status?, followUpState?, email?, observations?, product?, propertyValue? }`
  - Defaults: `status="Primeiro Atendimento"`, `followUpState="Sem Follow Up"`
  - 201 → `{ id, name, ... }`
- GET `${BASE_URL}/clients?q=<texto>`
  - 200 → `[{ ... }]` (máx. 200, ordenado por `updatedAt desc`)
- GET `${BASE_URL}/clients/{id}`
  - 200 → `{ ... , interactions: [...] }`
- PUT `${BASE_URL}/clients/{id}`
  - Campos: `name, phone, email, observations, product, propertyValue, status, followUpState`
  - 200 → `{ id, name, ... }`
- DELETE `${BASE_URL}/clients/{id}` (ADMIN)
  - 204
- GET `${BASE_URL}/clients/export`
  - 200 → `text/csv`

Interações
- POST `${BASE_URL}/interactions`
  - Body: `{ clientId, type, observation?, explicitNext? }`
  - Efeitos:
    - `STATUS_CHANGE` + `explicitNext` → altera `client.status`
    - `FOLLOW_UP_SCHEDULED` → `client.followUpState = "Ativo"`
    - `FOLLOW_UP_*` (DONE/CANCELED/CANCELLED/LOST/CLOSED) → `client.followUpState = "Sem Follow Up"`
  - 201

Analytics
- GET `${BASE_URL}/analytics/broker-kpis`
  - 200 → `{ followUpAtrasado, leadsEmTratativa, leadsPrimeiroAtendimento, totalLeads }`
- GET `${BASE_URL}/analytics/productivity?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&brokerId?=`
  - 200 → `{ series: [ { date, count } ] }`
- GET `${BASE_URL}/analytics/funnel?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&brokerId?=`
  - 200 → `{ stages: { "Primeiro Atendimento": n, "Em Tratativa": n, "Proposta": n, "Fechado": n } }`

Health
- GET `${BASE_URL}/health` → `{ "status": "ok" }`

Erros
- Formato: `{ "error": "Mensagem...", "detail"?: "..." }`
- Códigos: 400, 401, 403, 404, 409, 500

RBAC
- `BROKER`: vê somente `owner_id == sub`
- `MANAGER`/`ADMIN`: vê tudo; `ADMIN` requerido para deletar clientes
