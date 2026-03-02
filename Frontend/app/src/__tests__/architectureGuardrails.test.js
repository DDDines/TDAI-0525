import fs from "fs";
import path from "path";

const SRC_ROOT = path.resolve("src");
const VALID_EXTENSIONS = new Set([".js", ".jsx", ".ts", ".tsx"]);
const SKIP_DIRS = new Set(["__tests__", "__mocks__", "dist", "node_modules"]);

function collectSourceFiles(rootDir) {
  const files = [];
  const queue = [rootDir];

  while (queue.length > 0) {
    const current = queue.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        if (!SKIP_DIRS.has(entry.name)) {
          queue.push(fullPath);
        }
        continue;
      }

      if (!VALID_EXTENSIONS.has(path.extname(entry.name))) {
        continue;
      }
      files.push(fullPath);
    }
  }

  return files;
}

describe("frontend architecture guardrails", () => {
  test("frontend source does not use synthetic _TopLevelFunctionSurface wrappers", () => {
    const offenders = [];

    for (const filePath of collectSourceFiles(SRC_ROOT)) {
      const source = fs.readFileSync(filePath, "utf-8");
      if (source.includes("_TopLevelFunctionSurface")) {
        offenders.push(path.relative(SRC_ROOT, filePath));
      }
    }

    expect(offenders).toEqual([]);
  });

  test("frontend source does not contain TODO/FIXME placeholders", () => {
    const offenders = [];
    const blocked = ["TODO", "FIXME"];

    for (const filePath of collectSourceFiles(SRC_ROOT)) {
      const source = fs.readFileSync(filePath, "utf-8");
      for (const marker of blocked) {
        if (source.includes(marker)) {
          offenders.push(`${path.relative(SRC_ROOT, filePath)} :: ${marker}`);
        }
      }
    }

    expect(offenders).toEqual([]);
  });

  test("frontend module comments avoid generic boilerplate wording", () => {
    const offenders = [];
    const blocked = ["Implements frontend behavior for"];

    for (const filePath of collectSourceFiles(SRC_ROOT)) {
      const source = fs.readFileSync(filePath, "utf-8");
      for (const fragment of blocked) {
        if (source.includes(fragment)) {
          offenders.push(`${path.relative(SRC_ROOT, filePath)} :: ${fragment}`);
        }
      }
    }

    expect(offenders).toEqual([]);
  });
});

