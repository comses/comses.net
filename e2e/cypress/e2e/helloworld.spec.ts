describe("Hello world vue 3 component", () => {
  it("Should render and function correctly when clicking the button", { scrollBehavior: false }, () => {
    cy.visit("/codebases");
    cy.get("#app").within(() => {
      cy.get("h1")
        .should("contain", "Vue 3 Component");
      cy.get("button").scrollIntoView()
      cy.get("button")
        .should("contain", "click me")
        .click();
      cy.get("p")
        .should("contain", "count: 1"); 
    });
  });
});
