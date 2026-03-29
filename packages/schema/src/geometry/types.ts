import type { z } from "zod";
import type {
  boundingBoxSchema,
  edgeSchema,
  faceSchema,
  groupSchema,
  serializedGeometrySchema,
  vertexSchema,
} from "./schema.generated";

export type BoundingBox = z.infer<typeof boundingBoxSchema>;
export type Edge = z.infer<typeof edgeSchema>;
export type Face = z.infer<typeof faceSchema>;
export type Group = z.infer<typeof groupSchema>;
export type Vertex = z.infer<typeof vertexSchema>;
export type SerializedGeometry = z.infer<typeof serializedGeometrySchema>;
