export function validateAlphanumericCharacters(value: string) {
  if (!/^[a-zA-Z0-9_.-]*$/.test(value)) {
    return 'Valid characters: a-Z , 0-9 , dashes, underscores, and periods';
  }

  return true;
}

export function validateEmail(value: string) {
  if (!/^[^@]+@[^@]+\.[^@]+$/.test(value)) {
    return 'Please enter a valid email';
  }

  return true;
}
