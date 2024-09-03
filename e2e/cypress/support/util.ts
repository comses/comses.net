/**
 * Get an element by its data-cy attribute
 * @param {string} value - value of the data-cy attribute
 */
export function getDataCy(value: string): Cypress.Chainable {
  return cy.get(`[data-cy="${value}"]`);
}
