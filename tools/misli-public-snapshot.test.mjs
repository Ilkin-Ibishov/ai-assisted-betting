import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const script = fileURLToPath(new URL("./misli-public-snapshot.mjs", import.meta.url));

test("snapshot producer rejects unsafe post path before browsing", () => {
  const result = spawnSync(
    process.execPath,
    [
      script,
      "--post-url",
      "https://example.com/not-the-ingest-endpoint",
      "--token",
      "secret",
    ],
    { encoding: "utf-8" },
  );

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Snapshot post URL must target/);
});

test("snapshot producer requires token when post url is configured", () => {
  const result = spawnSync(
    process.execPath,
    [
      script,
      "--post-url",
      "https://example.com/api/live/snapshots/latest/misli-public",
    ],
    {
      encoding: "utf-8",
      env: { ...process.env, SNAPSHOT_INGEST_TOKEN: "" },
    },
  );

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /required with --post-url/);
});
