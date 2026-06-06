import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { safeRelativeRedirect } from "./navigation";

describe("safeRelativeRedirect", () => {
  it("allows relative paths", () => {
    assert.equal(safeRelativeRedirect("/dashboard?tab=payouts"), "/dashboard?tab=payouts");
  });

  it("falls back for absolute URLs", () => {
    assert.equal(safeRelativeRedirect("https://evil.test/phish"), "/dashboard");
  });

  it("falls back for protocol-relative URLs", () => {
    assert.equal(safeRelativeRedirect("//evil.test/phish"), "/dashboard");
  });

  it("falls back for missing values", () => {
    assert.equal(safeRelativeRedirect(null), "/dashboard");
  });

  it("falls back for backslashes and control characters", () => {
    assert.equal(safeRelativeRedirect("/\\evil"), "/dashboard");
    assert.equal(safeRelativeRedirect("/dashboard\nSet-Cookie:bad=1"), "/dashboard");
  });
});
