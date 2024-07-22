export function parseHashParams(hash: string) {
  const hashParams = new URLSearchParams(hash.substring(1));
  const params: Record<string, string> = {};
  hashParams.forEach((value, key) => {
    params[key] = value;
  });
  return params;
}

export function stringToUint8Array(str: string) {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(str);
  return new Uint8Array(bytes);
}
