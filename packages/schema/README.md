# @ionforge/schema

Zod schemas and TypeScript types for IonForge data formats.

## Installation

```bash
pnpm add @ionforge/schema
```

## Usage

```typescript
import { GeometrySchema } from "@ionforge/schema/geometry";

const result = GeometrySchema.safeParse(data);
if (result.success) {
  const geometry = result.data;
}
```

## License

Apache-2.0 — see [LICENSE](./LICENSE) for details.
