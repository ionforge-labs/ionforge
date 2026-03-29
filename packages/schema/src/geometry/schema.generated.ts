// THIS FILE IS AUTO-GENERATED — DO NOT EDIT
// Regenerate with: just schema-generate

import { z } from "zod";

export const boundingBoxSchema = z.object({ "size": z.tuple([z.number(),z.number(),z.number()]), "voltage": z.number() });

export const edgeSchema = z.object({ "id": z.string(), "v0": z.string(), "v1": z.string(), "faceIds": z.array(z.string()).default([]) });

export const faceSchema = z.object({ "id": z.string(), "vertexIds": z.array(z.string()).min(3), "edgeIds": z.array(z.string()) });

export const groupSchema = z.object({ "id": z.string(), "name": z.string(), "color": z.string(), "voltage": z.number().nullable(), "faceIds": z.array(z.string()).default([]), "edgeIds": z.array(z.string()).default([]) });

export const vertexSchema = z.object({ "id": z.string(), "position": z.tuple([z.number(),z.number(),z.number()]) });

export const serializedGeometrySchema = z.object({
  version: z.literal(1),
  units: z.literal("m"),
  vertices: z.array(vertexSchema),
  edges: z.array(edgeSchema),
  faces: z.array(faceSchema),
  boundingBox: boundingBoxSchema,
  groups: z.array(groupSchema),
  groupOrder: z.array(z.string()),
});
