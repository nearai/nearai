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

export function stringToHtmlAttribute(str: string) {
  return str.replace(/[^a-zA-Z0-9_.-]*/g, '');
}

export function stringToPotentialJson(str: string) {
  const trimmed = str.trim();
  let shouldAttemptParse = false;

  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    shouldAttemptParse = true;
  } else if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
    shouldAttemptParse = true;
  }

  let json: Record<string, unknown> | null = null;

  if (shouldAttemptParse) {
    try {
      json = JSON.parse(str) as Record<string, unknown>;
    } catch (error) {
      console.warn(
        'Failed to parse string as JSON via stringToPotentialJson()',
        str,
        error,
      );
    }
  }

  return json;
}
