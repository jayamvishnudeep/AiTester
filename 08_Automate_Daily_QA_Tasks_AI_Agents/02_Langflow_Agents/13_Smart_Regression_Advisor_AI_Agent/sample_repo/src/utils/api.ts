export async function request(path: string, init?: RequestInit): Promise<Response> {
  const base = process.env.BASE_URL ?? 'https://staging.shopfront.example.com';
  return fetch(`${base}${path}`, init);
}
