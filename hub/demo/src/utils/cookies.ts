export function parseCookies(str: string) {
  const result: Record<string, string> = {};

  return str
    .split(';')
    .map((v) => v.split('='))
    .reduce((result, v) => {
      const key = v[0];
      const value = v[1];

      if (key && value) {
        result[decodeURIComponent(key)] = decodeURIComponent(value);
      }

      return result;
    }, result);
}
