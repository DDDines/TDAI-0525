# Commenting Standard

## Objective
Make the codebase readable for any engineer without relying on tribal knowledge.

## Mandatory documentation layers

1. Module docstring
- Explain what the module does in the architecture.
- State main responsibilities and boundaries.

2. Class docstring
- Explain role, dependencies, and lifecycle.
- Clarify what the class owns and what it delegates.

3. Public method/function docstring
- Describe behavior and intent.
- Document inputs, outputs, exceptions, and side effects.

4. Private method/function docstring
- Explain why the helper exists and which rule/heuristic it encapsulates.

5. Inline comments
- Use only for non-obvious decisions, heuristics, or tradeoffs.
- Do not comment line-by-line obvious code.

## Writing rules

- Keep comments factual and implementation-aware.
- Keep comments synchronized with code behavior.
- Prefer concise language over long prose.
- Avoid placeholders like `TODO`, `FIXME`, `later`.
- Avoid boilerplate descriptions that add no meaning.

## Forbidden boilerplate

Do not use generic patterns such as:

- `Execute <name>.`
- `This callable is documented to make behavior explicit for readers.`
- `Encapsulates one responsibility in the backend architecture.`
- `This module contains backend application/runtime logic and is fully documented...`

Each docstring must describe real behavior, boundary, or decision relevant to that symbol.

## Docstring shape (recommended)

```python
def some_method(arg1: int, arg2: str) -> bool:
    """Validate business rule X and persist the result.

    Args:
        arg1: Identifier for the target entity.
        arg2: User provided value to evaluate.

    Returns:
        True when the rule passes and persistence succeeds.

    Raises:
        ValueError: When input is invalid.
    """
```

## Scope default

- Apply to all Python files under `Backend/`.
- Exceptions allowed only for generated/migration files (`alembic/`, migrations) and must be explicit.

## Frontend scope

- Apply module comments to all files under `Frontend/app/src` (`.js`, `.jsx`, `.ts`, `.tsx`).
- Each module comment must describe the feature/domain responsibility of the file.
- Frontend comments must also avoid generic boilerplate and placeholder markers.
