Backend (Flask) — Supabase JWT via JWKS

Overview
- Valida JWT do Supabase via JWKS (RS256), com cache de 15 minutos.
- Mantém mapeamento 1:1: auth.users.id → users.id → profiles.user_id.
- Bootstrap automático de users/profiles no primeiro acesso.
- Endpoints unificados em `/api`: `GET /api/me`, `/api/clients`, `/api/interactions`.
- Rotas protegidas usam `@auth_required` (decorator) e nunca confiam em `owner_id` enviado pelo body.

Variáveis de ambiente (.env)
- SUPABASE_URL: ex. https://<project-id>.supabase.co (obrigatória)
- SUPABASE_JWT_AUD: audiência esperada (opcional)
- SUPABASE_JWT_ISS: issuer esperado (default: `${SUPABASE_URL}/auth/v1`)
- ALLOWED_ROLES: BROKER,MANAGER,ADMIN (default)
- DATABASE_URL: string de conexão PostgreSQL
- CORS_ORIGINS: domínios permitidos
- FLASK_ENV: development|production

Modelos
- User: `id (UUID, PK)`, `email`, `name`, `role (Enum: BROKER|MANAGER|ADMIN)`, `created_at`.
- Profile: `id (UUID, PK)`, `user_id (FK->users.id, unique)`, `phone_number`, `address`, `avatar_url`, `is_active (bool)`, `metadata (JSON/JSONB)`, `created_at`, `updated_at`.
- Client: inclui `owner_id -> users.id`.
- Interaction: inclui `client_id`, `user_id`.

JWT (utils/supabase_jwt.py)
- Download do JWKS em `${SUPABASE_URL}/auth/v1/keys` (cache 15 min com cachetools).
- Seleção da chave por `kid` do header.
- Validação das claims: `iss`, (`aud` se configurado), `exp/iat/nbf`.
- Retorna claims com `sub`, `email`, `role` (fallback para BROKER; respeita ALLOWED_ROLES).
- Expostos:
  - `verify_supabase_jwt(bearer_token: str) -> dict`
  - `auth_required(fn)` — injeta `g.user_claims`, `g.user_id`, `g.email`, `g.role`.
  - `get_or_create_user_and_profile(auth_user_id, email)` — idempotente.

Endpoints
- GET `/api/me`
  - Header: `Authorization: Bearer <access_token>` (Supabase)
  - Passos: valida token → bootstrap (user/profile) → retorna payload padronizado:
    {
      "user": { "id":"uuid", "email":"...", "name":"...", "role":"BROKER" },
      "profile": { "phoneNumber":null, "address":null, "avatarUrl":null, "isActive":true },
      "routing": { "target":"/app", "reason":"role=BROKER" }
    }
  - Regras de roteamento: ADMIN→/admin, MANAGER→/manager, BROKER→/app; se profile inativo → /onboarding.

- GET `/api/clients` (protegida)
  - Usa `@auth_required`. Filtro por `owner_id = g.user_id`.
  - Query: `q`, `status`, `page`, `pageSize`; retorna `{ items, page, pageSize }`.

- POST `/api/clients` (protegida)
  - Ignora `owner_id` do body; usa `g.user_id`.
  - Body: `{ name, phone, email?, source?, status?, followUpState?, ... }`.
  - 201: cliente criado.

- GET `/api/interactions?client_id=<uuid>` (protegida)
  - Retorna interações apenas se `client.owner_id = g.user_id`.

Como o Front usa (/api/me)
// Supabase JS
const { data: { session } } = await supabase.auth.getSession();
const token = session?.access_token;

const me = await fetch('/api/me', {
  headers: { Authorization: `Bearer ${token}` }
}).then(r => r.json());

// Decidir rota
const map = { ADMIN:'/admin', MANAGER:'/manager', BROKER:'/app' };
const target = me?.routing?.target ?? map[me?.user?.role] ?? '/onboarding';
router.navigate(target);

Segurança
- Nunca aceitar `owner_id` do body (sempre usar `g.user_id`).
- Rate limit básico (60 req/min por IP) embutido no `@auth_required`.
- Logar falhas de JWT (nível WARNING).
- CORS restrito (`CORS_ORIGINS`).

Como rodar os testes (Pytest)
- Os testes unitários adicionados cobrem validação via JWKS e `/api/me`.
- Exemplo para rodar apenas os novos testes:
  `pytest -k "test_me or test_auth" -q`

