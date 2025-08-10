export function getGenerateEndpoint(docId: string): string {
  const baseUrl = (import.meta as any)?.env?.VITE_API_BASE_URL ?? "";
  const normalizedBase =
    typeof baseUrl === "string" ? baseUrl.replace(/\/+$/, "") : "";
  const path = `/api/generate/${encodeURIComponent(docId)}`;
  return `${normalizedBase}${path}`;
}
