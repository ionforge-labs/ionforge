// THIS FILE IS AUTO-GENERATED — DO NOT EDIT
// Regenerate with: just sdk-generate

import { z } from "zod";

export const boundingBoxSchema = z.object({ "size": z.tuple([z.number(),z.number(),z.number()]), "voltage": z.number() });

export const edgeSchema = z.object({ "id": z.string(), "v0": z.string(), "v1": z.string(), "faceIds": z.array(z.string()).optional() });

export const faceSchema = z.object({ "id": z.string(), "vertexIds": z.array(z.string()).min(3), "edgeIds": z.array(z.string()) });

export const groupSchema = z.object({ "id": z.string(), "name": z.string(), "color": z.string(), "voltage": z.union([z.number(), z.null()]), "faceIds": z.array(z.string()).optional(), "edgeIds": z.array(z.string()).optional() });

export const vertexSchema = z.object({ "id": z.string(), "position": z.tuple([z.number(),z.number(),z.number()]) });

export const serializedGeometrySchema = z.object({
  version: z.literal(1).default(1).optional(),
  units: z.literal("m").default("m").optional(),
  vertices: z.array(vertexSchema),
  edges: z.array(edgeSchema),
  faces: z.array(faceSchema),
  boundingBox: boundingBoxSchema,
  groups: z.array(groupSchema),
  groupOrder: z.array(z.string()),
});
