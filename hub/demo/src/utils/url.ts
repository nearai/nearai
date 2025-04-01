export function getHashParams(hash: string) {
  const hashParams = new URLSearchParams(hash.substring(1));
  const params: Record<string, string> = {};
  hashParams.forEach((value, key) => {
    params[key] = value;
  });
  return params;
}

export function getQueryParams() {
  const searchParams = new URLSearchParams(window.location.search);
  const params: Record<string, string> = {};

  searchParams.forEach((value, key) => {
    params[key] = value;
  });

  return params;
}

export function getPrimaryDomainFromUrl(str: string | null | undefined) {
  if (!str) return null;

  try {
    const url = new URL(str);
    return url.hostname.replace('www.', '');
  } catch (_error) {
    return null;
  }
}
