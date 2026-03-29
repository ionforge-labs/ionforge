/**
 * Generate Zod schemas from the IonForge JSON Schema.
 *
 * Handles $ref resolution and prefixItems (tuples) that json-schema-to-zod
 * does not support natively.
 */
const { jsonSchemaToZod } = require("json-schema-to-zod");
const fs = require("fs");
const path = require("path");

const REPO_ROOT = path.resolve(__dirname, "../../..");
const SCHEMA_DIR = path.resolve(__dirname, "..");
const SCHEMA_FILE = path.join(SCHEMA_DIR, "geometry-schema.json");
const OUTPUT_FILE = path.join(SCHEMA_DIR, "src/geometry/schema.generated.ts");

const schema = JSON.parse(fs.readFileSync(SCHEMA_FILE, "utf8"));
const defs = schema["$defs"] || {};

/** Replace prefixItems tuples with a structure json-schema-to-zod understands. */
function fixTuples(obj) {
  if (obj === null || typeof obj !== "object") return obj;
  if (Array.isArray(obj)) return obj.map((x) => fixTuples(x));

  // Pydantic emits prefixItems for tuple[float, float, float]
  if (obj.prefixItems && obj.type === "array") {
    return {
      ...obj,
      type: "array",
      items: obj.prefixItems.map((item) => fixTuples(item)),
      minItems: obj.minItems,
      maxItems: obj.maxItems,
      // Mark for post-processing
      _isTuple: true,
      prefixItems: undefined,
    };
  }

  const result = {};
  for (const [k, v] of Object.entries(obj)) {
    result[k] = fixTuples(v);
  }
  return result;
}

/** Inline all $ref pointers. */
function deref(obj) {
  if (obj === null || typeof obj !== "object") return obj;
  if (obj["$ref"]) {
    const name = obj["$ref"].replace("#/$defs/", "");
    return deref(JSON.parse(JSON.stringify(defs[name])));
  }
  if (Array.isArray(obj)) return obj.map((x) => deref(x));
  const result = {};
  for (const [k, v] of Object.entries(obj)) {
    if (k === "$defs") continue;
    result[k] = deref(v);
  }
  return result;
}

/** Generate Zod code for a single schema definition. */
function generateSchema(def) {
  const resolved = fixTuples(deref(def));
  delete resolved.title;
  let code = jsonSchemaToZod(resolved, {
    module: "none",
    noImport: true,
  });
  // Replace z.array(z.any()).min(3).max(3) patterns from tuples with z.tuple()
  code = fixTupleCode(code, resolved);
  return code;
}

/** Post-process to replace array patterns with tuple for marked fields. */
function fixTupleCode(code, schema) {
  if (!schema || typeof schema !== "object") return code;

  // Find tuple fields by walking the schema
  const tupleFields = findTupleFields(schema);
  for (const { minItems, maxItems, itemTypes } of tupleFields) {
    if (minItems === maxItems && itemTypes.length === minItems) {
      const arrayPattern = `z.array(z.any()).min(${minItems}).max(${maxItems})`;
      const tupleItems = itemTypes.map((t) => `z.${t}()`).join(", ");
      const tupleReplacement = `z.tuple([${tupleItems}])`;
      code = code.split(arrayPattern).join(tupleReplacement);
    }
  }
  return code;
}

function findTupleFields(obj, results = []) {
  if (obj === null || typeof obj !== "object") return results;
  if (obj._isTuple && obj.items) {
    results.push({
      minItems: obj.minItems,
      maxItems: obj.maxItems,
      itemTypes: obj.items.map((i) => i.type || "any"),
    });
  }
  if (Array.isArray(obj)) {
    obj.forEach((x) => findTupleFields(x, results));
  } else {
    Object.values(obj).forEach((v) => findTupleFields(v, results));
  }
  return results;
}

/**
 * Post-process generated Zod code for a $def schema:
 * - Non-required array fields: .optional() → .default([])
 * - anyOf [{type:"number"},{type:"null"}]: z.union([z.number(), z.null()]) → z.number().nullable()
 */
function fixDefaults(code, def) {
  const props = def.properties || {};
  const req = new Set(def.required || []);

  for (const [key, prop] of Object.entries(props)) {
    if (req.has(key)) continue;

    // Non-required array fields should default to [] rather than be optional
    if (prop.type === "array") {
      // Match the field pattern: "fieldName": <anything>.optional()
      // Use [^,}]+ to capture the value up to .optional() (no commas/braces)
      const re = new RegExp(
        `("${key}":\\s*[^,}]+)\\.optional\\(\\)`,
      );
      code = code.replace(re, "$1.default([])");
    }
  }

  // z.union([z.number(), z.null()]) → z.number().nullable()
  code = code.replace(
    /z\.union\(\[z\.number\(\),\s*z\.null\(\)\]\)/g,
    "z.number().nullable()",
  );

  return code;
}

// Build output
const lines = [
  "// THIS FILE IS AUTO-GENERATED \u2014 DO NOT EDIT",
  "// Regenerate with: just schema-generate",
  "",
  'import { z } from "zod";',
  "",
];

// Named sub-schemas
for (const [name, def] of Object.entries(defs)) {
  const varName = name.charAt(0).toLowerCase() + name.slice(1) + "Schema";
  let code = generateSchema(def);
  code = fixDefaults(code, def);
  lines.push(`export const ${varName} = ${code};`);
  lines.push("");
}

// Root schema — reference the named sub-schemas instead of inlining
const rootProps = schema.properties || {};
const required = new Set(schema.required || []);

const rootFields = [];
for (const [key, prop] of Object.entries(rootProps)) {
  let fieldCode;
  if (prop["$ref"]) {
    const refName = prop["$ref"].replace("#/$defs/", "");
    fieldCode =
      refName.charAt(0).toLowerCase() + refName.slice(1) + "Schema";
  } else {
    const resolved = fixTuples(deref(prop));
    delete resolved.title;
    fieldCode = jsonSchemaToZod(resolved, {
      module: "none",
      noImport: true,
    });
  }

  if (prop.items && prop.items["$ref"]) {
    const refName = prop.items["$ref"].replace("#/$defs/", "");
    const itemSchema =
      refName.charAt(0).toLowerCase() + refName.slice(1) + "Schema";
    fieldCode = `z.array(${itemSchema})`;
  }

  if (!required.has(key)) {
    // Fields with const+default (e.g. version: Literal[1] = 1) should be
    // strict literals, not optional.  The only valid value IS the const,
    // so strip the redundant .default() that jsonSchemaToZod adds.
    if (prop.const !== undefined && prop.default !== undefined) {
      fieldCode = fieldCode.replace(/\.default\([^)]*\)/, "");
    } else {
      fieldCode += ".optional()";
    }
  }

  rootFields.push(`  ${key}: ${fieldCode},`);
}

lines.push(`export const serializedGeometrySchema = z.object({`);
lines.push(rootFields.join("\n"));
lines.push(`});`);

fs.writeFileSync(OUTPUT_FILE, lines.join("\n") + "\n");
console.log(`Written to ${OUTPUT_FILE}`);
