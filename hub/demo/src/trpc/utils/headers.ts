export function conditionallyIncludeAuthorizationHeader(
  authorization: string | null | undefined,
  headers: Record<string, string>,
) {
  return authorization ? { ...headers, Authorization: authorization } : headers;
}
