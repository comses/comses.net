//test ability to browse/download codebases
describe("Browse Codebases", () => {
  it("should browse the model library and be able to enter a search query", () => {
    cy.visit("/"); // visit homepage
    cy.visit("/codebases");
    assert(cy.get("h1").contains("Computational Model Library"));
  });
});

//download codebase
describe("Download Codebases", () => {
  it("should download a codebase", () => {
    // Navigate to the first 'search-result', find the 'a' tag within the 'title' div, and click it
    cy.get(".search-result", { timeout: 10000 })
      .first()
      .find(".title a")
      .click();
  });
});
