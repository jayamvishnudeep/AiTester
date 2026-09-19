export function formatPrice(pennies: number): string {
  return `£${(pennies / 100).toFixed(2)}`;
}

export function addTax(pennies: number, ratePercent: number): number {
  return Math.round(pennies * (1 + ratePercent / 100));
}
