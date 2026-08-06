import projectTemplate from "../../../config/project.template.json";

const localConfigModules = import.meta.glob("../../../config/*.json", {
  eager: true,
  import: "default"
}) as Record<string, Record<string, unknown>>;
const projectConfig = localConfigModules["../../../config/project.json"] ?? projectTemplate;
const userProjectConfig = localConfigModules["../../../config/user.project.json"] ?? {};
const mergedProjectConfig = deepMerge(projectConfig, userProjectConfig) as typeof projectTemplate;

export const API_BASE_URL = resolveApiBaseUrl(mergedProjectConfig.frontend.apiBaseUrl);

export function resolveApiBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.trim().replace(/\/+$/, "");
}

function deepMerge<TBase extends Record<string, unknown>>(
  base: TBase,
  override: Record<string, unknown>
): TBase {
  const merged: Record<string, unknown> = { ...base };
  for (const [key, value] of Object.entries(override)) {
    const current = merged[key];
    merged[key] = isPlainObject(current) && isPlainObject(value)
      ? deepMerge(current, value)
      : value;
  }
  return merged as TBase;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
