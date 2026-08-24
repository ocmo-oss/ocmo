/** All OCMO API request and response types. */

export interface ErrorResponse {
  error: string
}

// ── System ─────────────────────────────────────────────────────────────────

export interface HealthCheckDetail {
  status: 'ok' | 'error'
  message?: string
}

export interface HealthResponse {
  status: 'ok' | 'error'
  checks: Record<string, HealthCheckDetail>
}

export interface PublicOidcAuth {
  issuer: string
  client_id: string
  authorization_url: string
  token_url: string
  scopes: string
}

export interface PublicAuth {
  oidc: PublicOidcAuth
}

export interface BuiltinNamespacePaths {
  config: string[]
  secret: string[]
  schema: string[]
  order: string[]
}

export interface ReservedTags {
  config: string[]
  template: string[]
  secret: string[]
}

export interface VersionResponse {
  product: string
  version: string
  license: string
  license_name: string
  notice?: string
  config_metadata_key: string
  builtin_namespace_paths: BuiltinNamespacePaths
  reserved_tags: ReservedTags
  auth: PublicAuth
}

// ── Auth ───────────────────────────────────────────────────────────────────

export interface WhoAmIUserDetails {
  email?: string | null
  is_global_admin: boolean
  claims: Record<string, unknown>
}

export interface WhoAmIResolverDetails {
  namespace_id: number
  name: string
  token_number: number
}

export interface WhoAmIUser {
  auth_type: 'user'
  identifier: string
  display_name: string
  access_scope: string
  user_details: WhoAmIUserDetails
}

export interface WhoAmIResolver {
  auth_type: 'resolver'
  identifier: string
  display_name: string
  access_scope: string
  resolver_details: WhoAmIResolverDetails
}

export type WhoAmI = WhoAmIUser | WhoAmIResolver

export interface CanIRequest {
  namespace?: string
  operations: string[]
  resource?: string
}

export interface CanIResponse {
  allowed: Record<string, boolean>
}

// ── Namespace ──────────────────────────────────────────────────────────────

export interface Namespace {
  name: string
  description: string
  permissions_tag: string
  webhooks_tag: string
  git_sync_tag: string
  created_at: string
  updated_at: string
}

export interface NamespaceCreate {
  name: string
  description?: string
}

export interface NamespacePatch {
  description?: string
  permissions_tag?: string
  webhooks_tag?: string
  git_sync_tag?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  count: number
}

// ── Tree ───────────────────────────────────────────────────────────────────

export type ItemType = 'config' | 'template' | 'secret' | 'resolver' | 'folder'

export interface TreeNavigationNode {
  path: string
  name: string
  type: ItemType
  is_leaf: boolean
  description?: string
}

export interface NavigationBreadcrumb {
  path: string
  name: string
}

export interface NavigationResponse {
  item: TreeNavigationNode | null
  children: TreeNavigationNode[]
  breadcrumbs: NavigationBreadcrumb[]
  is_leaf: boolean
  count: number
}

export interface TagInfo {
  name: string
  version: number
}

export interface VersionEntry {
  version: number
  tags: string[]
  updater: string
  created_at: string
  deleted_at: string | null
  size: number | null
}

export interface VersionHistoryResponse {
  path: string
  type: ItemType
  tags: TagInfo[]
  versions: VersionEntry[]
  count: number
}

export interface AnyNode {
  path: string
  name: string
  type: ItemType
  description?: string
}

export interface ConfigNode extends AnyNode {
  type: 'config' | 'template'
  version: number
  content: string
  tags: TagInfo[]
  updater: string
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface SecretNode extends AnyNode {
  type: 'secret'
  version: number
  content?: string  // only when reveal=true
  tags: TagInfo[]
  updater: string
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface ResolverConfig {
  cast?: { format: string; options?: Record<string, unknown> }
  parameters?: Record<string, unknown>
  include?: string[]
  exclude?: string[]
  validate?: string
  validate_all?: string
  post_resolve?: string
  post_resolve_all?: string
}

export interface ResolverNode extends AnyNode {
  type: 'resolver'
  version: number
  author: string
  token1: string
  token1_last_used: string | null
  token2: string | null
  token2_last_used: string | null
  configuration?: ResolverConfig | string
  created_at: string
  updated_at: string
}

export interface ResolverTokenRotationResponse {
  token_number: 1 | 2
  token: string
}

export interface ResolverCreateResponse {
  path: string
  token1: string
}

export interface FolderNode extends AnyNode {
  type: 'folder'
  children_count: number
}

export type AnyExtendedNode = ConfigNode | SecretNode | ResolverNode | FolderNode

export interface DiffSide {
  path: string
  version: number
  content: string | null
  decryption_required?: boolean
}

export interface DiffResponse {
  from: DiffSide
  to: DiffSide
}

export interface TagPayload {
  tag: string
  version?: number
}

export interface LocationPayload {
  target_path: string
}

export interface DescribePayload {
  description: string
}

export interface DeleteResult {
  delete: string[]
}

export interface CopiedItems {
  copied: string[]
}

// ── Resolve ────────────────────────────────────────────────────────────────

export interface ResolveArtifact {
  name: string
  path: string
  url: string
  version: number
  cast: string
  from_cache: 'hit' | 'cast' | 'miss'
}

export interface ResolveParticipant {
  resource_type: 'config' | 'template' | 'secret'
  path: string
  version: number
  resolve_role: 'direct' | 'transitive'
  from_cache: boolean
}

export interface ResolveResponse {
  artifacts: ResolveArtifact[]
  trace?: Record<string, ResolveParticipant>
  trace_only?: boolean
}

export interface ResolveParametersResponse {
  path: string
  version: number
  requested_version?: string
  parameters: Record<string, ResolvedParameter>
}

export interface ResolvedParameter {
  type: 'projected' | 'dynamic' | 'secret' | string
  description?: string
  selector?: string | null
  secret_reference?: string | null
  declared_default?: unknown
  raw_value?: unknown
  effective_value?: unknown
  transformers_applied?: string[]
  caller_supplied?: boolean | null
}

export interface CastFormatInfo {
  format: string
  options_schema: Record<string, unknown>
}

export interface CastFormatsList {
  formats: CastFormatInfo[]
}

export interface PropagationTargetResult {
  path: string
  status: 'updated' | 'unchanged' | 'skipped' | 'error'
  version: number | null
  reason: string | null
}

export interface PropagationResult {
  source_path: string
  source_version: number
  trigger: string
  targets: PropagationTargetResult[]
}

// ── Locks ──────────────────────────────────────────────────────────────────

export interface Lock {
  path: string
  reason: string
  locked_by: string
  created_at: string
  updated_at: string
  expires_at: string | null
}

export interface LocksList {
  locks: Lock[]
  count: number
}

export interface LockPayload {
  reason: string
  expires_at?: string
}

// ── Global Permissions ─────────────────────────────────────────────────────

export interface GlobalPermissionActor {
  kind: 'User'
  claims: Record<string, string>
}

export interface GlobalPermissionGate {
  actors: GlobalPermissionActor[]
}

// Shape of the rule content (used for create/update payloads and nested in GET responses).
export interface GlobalPermissionRulePayload {
  id?: string
  description?: string
  namespace: string
  read?: GlobalPermissionGate
  write?: GlobalPermissionGate
  delete?: GlobalPermissionGate
  audit?: GlobalPermissionGate
}

// API GET response: DB envelope wrapping the rule content.
export interface GlobalPermissionRule {
  id: string          // DB UUID
  position: number
  rule: GlobalPermissionRulePayload
  created_at: string
  updated_at: string
}

export interface GlobalPermissionRulesList {
  rules: GlobalPermissionRule[]
  count: number
}

export interface GlobalPermissionMovePaylod {
  position: number
}

// ── Audit ──────────────────────────────────────────────────────────────────

export interface AuditParticipant {
  resource_type: string
  path: string
  version: number
  resolve_role: string
  from_cache: boolean
}

export interface AuditTimelineEntry {
  id: string
  occurred_at: string
  message: string
  operation?: string | null
  object_type?: string | null
  object_id?: string | null
  object_version?: number | null
  subresource_type?: string | null
  subresource?: string | null
  auth_id: string
  auth_email?: string | null
  auth_type: string
  permission_ok?: boolean | null
  event_kind: string
}

export interface AuditEvent {
  id: string
  occurred_at: string
  client_ip?: string | null
  user_agent?: string | null
  auth_id: string
  auth_email?: string | null
  auth_type: string
  token_number?: number | null
  namespace?: string | null
  http_method: string
  api_endpoint: string
  object_type?: string | null
  object_id?: string | null
  object_version?: number | null
  operation?: string | null
  subresource_type?: string | null
  subresource?: string | null
  permission_ok?: boolean | null
  error?: string | null
  resolve_type?: string | null
  from_cache?: boolean | null
  parent_event_id?: string | null
  event_kind: string
}
