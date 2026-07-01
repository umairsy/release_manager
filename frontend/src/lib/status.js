// Shared status → Badge theme mapping used across views.
const THEMES = {
  Passed: "green",
  pass: "green",
  Partial: "orange",
  Failed: "red",
  fail: "red",
  Running: "blue",
  Queued: "blue",
  Draft: "gray",
  Skipped: "gray",
  skip: "gray",
};

export function statusTheme(status) {
  return THEMES[status] || "gray";
}

export const RUNNING_STATES = ["Queued", "Running"];
