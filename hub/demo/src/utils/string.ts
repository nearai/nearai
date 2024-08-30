export function stringToUint8Array(str: string) {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(str);
  return new Uint8Array(bytes);
}
