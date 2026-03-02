import fs from "fs";
import path from "path";

const SRC_ROOT = path.resolve("src");
const VALID_EXTENSIONS = new Set([".js", ".jsx", ".ts", ".tsx"]);
const SKIP_DIRS = new Set(["__tests__", "__mocks__", "dist", "node_modules"]);

const BLOCKED_BOILERPLATE = [
  '"""Execute ',
  "This callable is documented to make behavior explicit for readers.",
  "Encapsulates one responsibility in the backend architecture.",
  "This module contains backend application/runtime logic and is fully",
];

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

function hasModuleComment(source) {
  const trimmed = source.trimStart();
  return trimmed.startsWith("/**");
}

describe("frontend commenting guardrails", () => {
  test("all frontend modules include a contextual module comment", () => {
    const offenders = [];
    for (const filePath of collectSourceFiles(SRC_ROOT)) {
      const source = fs.readFileSync(filePath, "utf-8");
      if (!hasModuleComment(source)) {
        offenders.push(path.relative(SRC_ROOT, filePath));
      }
    }
    expect(offenders).toEqual([]);
  });

  test("frontend source does not contain backend boilerplate docstrings", () => {
    const offenders = [];
    for (const filePath of collectSourceFiles(SRC_ROOT)) {
      const source = fs.readFileSync(filePath, "utf-8");
      for (const fragment of BLOCKED_BOILERPLATE) {
        if (source.includes(fragment)) {
          offenders.push(`${path.relative(SRC_ROOT, filePath)} :: ${fragment}`);
        }
      }
    }
    expect(offenders).toEqual([]);
  });
});
