import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Strip ANSI escape codes from log messages.
 * Backend logs include codes like ESC[93m for yellow, ESC[0m for reset, etc.
 */
export function stripAnsiCodes(text: string): string {
  const ansiRegex = /\x1b\[[0-9;]*[mGKH]/g;
  return text.replace(ansiRegex, "");
}
