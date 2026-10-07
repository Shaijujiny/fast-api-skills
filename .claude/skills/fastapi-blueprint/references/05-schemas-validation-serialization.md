# 5. Schemas, Validation & Serialization

Names below (`BaseSchema`, `ApiResponse`, `AppException`, `ErrorCode`) are defaults. If the project already has equivalents, follow those and keep the rules.

## 5.1 The `BaseSchema` base

All DTOs subclass `BaseSchema` (for example `app/schemas/base.py`), never bare `BaseModel`. A typical Pydantic v2 `model_config`:

- `from_attributes=True` (build a DTO straight from an ORM row)
- `populate_by_name=True` (accept snake_case or the alias)
- `alias_generator=to_camel` when the wire format is camelCase (pick one wire convention per project and keep it)
- `str_strip_whitespace=True` where free-text input is accepted

Keep Python attributes snake_case and let the alias generator produce the wire name. Do not hand-name camelCase attributes.

When a third party needs a different casing, serialize with `model_dump(by_alias=True)` or an explicit per-provider schema.

## 5.2 Naming and shape

- Requests end in `Request` (or `Create`/`Update`), responses in `Response` (`ExamSubmitRequest`, `TripBookingResponse`).
- Use `Field(...)` for descriptions, constraints, and defaults; `default_factory=list` / `dict` for collections (never a mutable literal default).
- Use `str`-valued `Enum` for closed choice sets (`BookingStatus`, `PaymentStatus`). Compare against `.value` when talking to the DB.
- Request schemas used with `Depends()` for query params must have all-optional or defaulted fields.
- Nest schemas for structured data; do not accept `dict` or `Any` for a structured payload.

## 5.3 Validation

- Put format and range checks in the schema (`Field(ge=0)`, `pattern`, `min_length`, validators) so FastAPI returns the standard 422 envelope before any service code runs.
- Reusable patterns (email, phone, IDs) live in one shared module (for example `app/core/patterns.py`); reuse them instead of re-writing regexes.
- Cross-field and business-rule validation (balance sufficient, slot still free, status transition allowed) belongs in the service and raises `AppException` with a localized message.
- Validators raise `ValueError` with a **message key**, not free text: the global validation handler reads the first error, picks the language from `Accept-Language`, and resolves the key through the i18n catalog. Plain-string errors (for example malformed JSON) are handled and stay 422.
- Reject unknown or unsafe input early: whitelist enum values, bound page size, and cap list lengths.

## 5.4 Declarative serialization aliases

Keep shared `Annotated` aliases in one module (for example `app/schemas/types.py`) that transform on serialize. Annotate the field and let Pydantic do the work.

| Alias (examples) | Effect |
|---|---|
| `Money2` | rounds a `Decimal` to 2 dp (or the currency's minor units) |
| `MaskedEmail`, `MaskedPhone`, `MaskedId` | mask PII for display |
| `LocalDatetime` | UTC datetime shown in the user's or business timezone |
| `DateStr` | formats a date to the project's agreed display format |

If a needed transform does not exist, add a new alias in that module. Do not scatter ad-hoc serializers across schemas or mask inside the service.

### Encryption schemes are separate concerns

- Encryption at rest (DB columns) and any transport-level payload protection are different mechanisms with different keys. Never reuse one for the other, and never mix their helpers.
- If a value stored encrypted must be shown to a client, decrypt it in one explicit, named step (a helper in `app/core/crypto.py`) and mask it; do not hide this inside a generic serializer.

## 5.5 Pagination schema

- Input: a shared `PaginationParams` (`offset`/`limit` or `page`/`page_size`, optional `search`) with bounded `limit`.
- Output: the page of rows plus `total_count`, and a per-status breakdown where sibling endpoints provide one.
- Repository methods return `tuple[Sequence[Model], int]`; the service maps rows to DTOs and builds the response.

## 5.6 Success and error envelopes

Success:

```python
return ApiResponse[PaymentResponse](
    status_code=status.HTTP_200_OK,
    code=ErrorCode.SUCCESS,
    message=self.message.payment_created,   # i18n key, never a literal
    data=payload,                           # a Pydantic model or None
)
```

Error (raise, never return):

```python
raise AppException(
    status_code=status.HTTP_403_FORBIDDEN,
    code=ErrorCode.FORBIDDEN,
    message=self.message.unauthorized,
)
```

- `AppException(status_code, code, message, data=None, headers=None)`.
- `ErrorCode` is grouped by status bucket (`AUTH_401_*`, `FORBIDDEN_403_*`, `NOT_FOUND_404_*`, `BUSINESS_422_*`, `BAD_REQUEST_400_*`, `SYSTEM_500_*`). Pick the code that matches the HTTP status you raise.
- Global handlers (registered in `app/main.py` or `app/core/exceptions.py`) cover `HTTPException`, DB errors, `RequestValidationError`, `AppException`, and a catch-all. They log (with traceback for non-HTTP errors) and return the standard envelope. Do not build ad-hoc error JSON in a service.
- Never expose SQL text, stack traces, or internal ids in `message`.

## 5.7 Dates, times, and money in schemas

- Money fields: `Decimal` (with a rounding alias on responses). No `float`.
- Store timestamps in UTC (timezone-aware) and convert to the user's or business timezone only on output.
- Get "now" from one shared helper (for example `app/core/clock.py`), never scattered `datetime.now()` calls.
- Date-only values returned to clients use one agreed format alias.

## 5.8 Sensitive fields in schemas

- A response schema field that holds PII uses a masking alias; a field that must never leave the server is simply not in the response schema.
- Request schemas that carry secrets (passwords, OTP, keys) must not be echoed back or logged. Use `SecretStr` where practical so they are hidden in `repr`.

## 5.9 Core rule

> Use Pydantic schemas for request **and** response validation. Avoid raw dictionaries for structured application data.

## 5.10 MUST / MUST NOT

```python
# MUST: a typed response schema, wrapped in the envelope
class UserResponse(BaseSchema):
    user_uuid: str
    name: str
    email: MaskedEmail

return ApiResponse[UserResponse](status_code=200, code=ErrorCode.SUCCESS,
                                 message=self.message.success, data=UserResponse.model_validate(user))
```

```python
# MUST NOT, when a response schema exists or can exist
return {"id": user.id, "name": user.name}
```

Use the return annotation `ApiResponse[UserResponse]` and/or `response_model=`; the typed `data` field gives the OpenAPI and validation benefit.

## 5.11 Pydantic v2 mechanics

| Topic | Rule |
|---|---|
| ORM to schema | `Schema.model_validate(orm_row)` (works because `from_attributes=True`) |
| Schema to dict | `model_dump(by_alias=True)` for provider payloads; `mode="json"` when serializing to JSON |
| Aliases | automatic via `alias_generator`; `populate_by_name=True` so snake_case input also works; set an explicit `alias` only when a provider needs an odd name |
| Optional vs nullable | `x: str | None = None` means optional and nullable; a required-but-nullable field is `x: str | None` with no default. Be deliberate; don't default to `None` to silence a validation error |
| Defaults | immutable defaults inline; `default_factory` for list/dict/datetime |
| Validation boundaries | structural checks in the schema (type, range, pattern, length); business checks needing DB or context in the service |
| Nested | compose schemas; don't pass nested raw dicts |
| `Annotated` | prefer the shared aliases module |
| Enums | `str`-valued `Enum`; compare with `.value` at the DB boundary |
| Custom validators | raise `ValueError` with a message key (resolved by the global handler into the user's language) |

## 5.12 External data is untrusted

Never use `response.json()` from a provider as-is. Parse it into a Pydantic model and handle `ValidationError` as an integration failure (section 8). The same goes for webhook bodies and uploaded JSON.
