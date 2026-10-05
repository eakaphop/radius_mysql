/** Operators accepted by the backend (kept in sync with utils/radius_attrs.py). */
export const RADIUS_OPERATORS = [
  ":=",
  "==",
  "=",
  "+=",
  "!=",
  ">",
  ">=",
  "<",
  "<=",
  "=~",
  "!~",
  "=*",
  "!*",
] as const;
