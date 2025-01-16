export function validateAlphanumericCharacters(value: string) {
  if (!/^[a-zA-Z0-9_.-]*$/.test(value)) {
    return 'Valid characters: a-Z , 0-9 , dashes, underscores, and periods';
  }

  return true;
}
