import { beforeEach, describe, expect, it } from "vitest";
import {
  readDefaultNamespace,
  writeDefaultNamespace,
} from "../../store/defaultNamespace";

const STORAGE_KEY = "ocmo-default-namespace";

describe("defaultNamespace storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null when unset", () => {
    expect(readDefaultNamespace()).toBeNull();
  });

  it("persists and reads a namespace name", () => {
    writeDefaultNamespace("production");
    expect(localStorage.getItem(STORAGE_KEY)).toBe("production");
    expect(readDefaultNamespace()).toBe("production");
  });

  it("clears the stored namespace", () => {
    writeDefaultNamespace("staging");
    writeDefaultNamespace(null);
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(readDefaultNamespace()).toBeNull();
  });
});
