# Purpose

Defines the local stdio MCP server for Cookidoo: entrypoint, environment-based configuration, authenticated session lifecycle, structured tool responses, and recoverable MCP error mapping.

## Requirements

### Requirement: Local stdio server entrypoint
The system SHALL provide a local MCP server entrypoint that runs over `stdio` and advertises the Cookidoo tool set without requiring callers to import Python code directly.

#### Scenario: Server starts successfully over stdio
- **WHEN** the local MCP server entrypoint is launched by an MCP host
- **THEN** the server initializes over `stdio`
- **AND** the host can discover the registered Cookidoo tools

### Requirement: Environment-based configuration
The server SHALL load Cookidoo credentials and default localization from local process configuration, and it MUST fail authenticated tool calls with actionable validation errors when required values are missing or invalid.

#### Scenario: Missing credentials are reported clearly
- **WHEN** an authenticated tool is called without configured Cookidoo credentials
- **THEN** the server returns an MCP tool error
- **AND** the error identifies the missing configuration inputs needed to proceed

#### Scenario: Invalid localization is rejected
- **WHEN** the configured country or language does not resolve to a valid Cookidoo localization
- **THEN** the server returns an MCP tool error
- **AND** the error explains that the caller must choose a valid localization

### Requirement: Authenticated session lifecycle
The server SHALL manage one authenticated Cookidoo client session per running MCP server process, including first-use login, token refresh, and graceful shutdown.

#### Scenario: First authenticated tool call performs login
- **WHEN** the first authenticated tool is invoked in a fresh MCP server process
- **THEN** the server creates an `aiohttp` session
- **AND** logs in with the configured Cookidoo credentials before calling the requested API method

#### Scenario: Expiring tokens are refreshed transparently
- **WHEN** an authenticated tool is invoked after the stored access token is expired or close to expiry
- **THEN** the server refreshes the token before executing the API call
- **AND** returns the requested tool result without requiring the caller to log in again manually

#### Scenario: Shutdown closes network resources
- **WHEN** the MCP server process shuts down
- **THEN** the server closes the shared `aiohttp` session cleanly

### Requirement: Structured responses
The server SHALL return JSON-compatible structured content for Cookidoo tool results so downstream MCP clients can inspect IDs, names, dates, and other follow-up fields without reparsing prose.

#### Scenario: Dataclass-based API results are serialized
- **WHEN** a tool returns data sourced from Cookidoo dataclass models
- **THEN** the server serializes the result into JSON-compatible structured content
- **AND** also provides a human-readable text summary for hosts that only render text

### Requirement: Recoverable MCP error mapping
The server SHALL translate known Cookidoo configuration, authentication, request, and parsing failures into MCP tool errors that preserve the transport and help the caller recover.

#### Scenario: Auth failures include recovery guidance
- **WHEN** the underlying Cookidoo client raises an authentication failure
- **THEN** the server returns an MCP tool error instead of crashing
- **AND** the error tells the caller to verify credentials and localization settings

#### Scenario: Upstream parsing failures remain actionable
- **WHEN** the underlying Cookidoo client cannot parse a Cookidoo response
- **THEN** the server returns an MCP tool error
- **AND** the error indicates that the upstream API response shape may have changed
