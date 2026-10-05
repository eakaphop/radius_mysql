/**
 * Access token kept in memory only (never localStorage — see CLAUDE.md
 * section 6). Plain module state so api/client.ts can read it without
 * depending on React or importing this feature's API module (would cycle).
 */

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}
