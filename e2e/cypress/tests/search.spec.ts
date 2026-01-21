import { getDataCy } from "../support/util";

describe("Sitewide search tests", () => {
  it("should display search results for a common query", () => {
    cy.visit("/search/?query=model");
    // should have at least one result
    getDataCy("search-result").should("have.length.greaterThan", 0);
  });

  it("should show no results message for nonsense query", () => {
    cy.visit("/search/?query=xyznonexistentquerythatshouldfindnothing123");
    // should have no results
    getDataCy("search-result").should("not.exist");
  });
});
