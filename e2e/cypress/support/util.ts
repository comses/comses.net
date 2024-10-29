/**
 * Get an element by its data-cy attribute
 * @param {string} value - value of the data-cy attribute
 */
export function getDataCy(value: string): Cypress.Chainable {
  return cy.get(`[data-cy="${value}"]`);
}

/**
 * Select the given day in the next month using the date picker
 * @param {Cypress.Chainable} element - container element of the datepicker input
 * @param {number} day - day to select
 */
export function selectNextMonthDate(element: Cypress.Chainable, day: number): Cypress.Chainable {
  element.first().click();
  return element.within(() => {
    cy.get('[aria-label="Next month"]').click();
    cy.contains(day).click();
  });
}
