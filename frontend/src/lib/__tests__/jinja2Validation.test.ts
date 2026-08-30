import { describe, expect, it } from "vitest";
import { validateJinja2Template } from "../jinja2Validation";

describe("validateJinja2Template", () => {
  it("accepts plain text without Jinja tags", () => {
    expect(validateJinja2Template("hello world")).toEqual({ valid: true });
  });

  it("accepts valid Jinja2 expressions", () => {
    expect(validateJinja2Template("foo: {{ bar }}\n")).toEqual({ valid: true });
  });

  it("accepts plain text followed by valid blocks", () => {
    const input = `Hello world

{% for a in test.items() %}
  {{ a }}
{% endfor %}`;
    expect(validateJinja2Template(input)).toEqual({ valid: true });
  });

  it("rejects empty content", () => {
    const result = validateJinja2Template("   \n");
    expect(result.valid).toBe(false);
    if (!result.valid) {
      expect(result.issue.message).toBe("Document content must not be empty");
    }
  });

  it("rejects unclosed variable tags", () => {
    const result = validateJinja2Template("{{ unclosed");
    expect(result.valid).toBe(false);
    if (!result.valid) {
      expect(result.issue.line).toBeGreaterThan(0);
      expect(result.issue.message).toMatch(/Invalid Jinja2/i);
    }
  });

  it("rejects unclosed block tags", () => {
    const result = validateJinja2Template("{% if true %}\nstill open");
    expect(result.valid).toBe(false);
    if (!result.valid) {
      expect(result.issue.line).toBe(1);
      expect(result.issue.message).toMatch(/unclosed/i);
    }
  });

  it("rejects mismatched endfor/endif with marker on the closing tag", () => {
    const input = `Hello world

{% for a in test.items() %}
  {{ a }}
  aaa
{% endif %}`;
    const result = validateJinja2Template(input);
    expect(result.valid).toBe(false);
    if (!result.valid) {
      expect(result.issue.line).toBe(6);
      expect(result.issue.message).toMatch(/expected {% endfor %}/i);
    }
  });
});
