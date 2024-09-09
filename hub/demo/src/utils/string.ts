export function stringToUint8Array(str: string) {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(str);
  return new Uint8Array(bytes);
}

export function toTitleCase(str: string) {
  return str.replace(
    /\w\S*/g,
    (text) => text.charAt(0).toUpperCase() + text.substring(1).toLowerCase(),
  );
}
