import { loginBeforeEach } from "./setup.spec";
import "cypress-file-upload";

//login
describe("Login", () => {
  it("should log into comses homepage with test user", function() {
    cy.fixture('codebase/data.json').then((data) => {
      const user = data.users[0];
      loginBeforeEach(user.username, user.password);
    })
  });
});


describe("Visit codebases page", () => {
  //codebases PAGE

  it("should visit the codebases page", () => {
    cy.visit("/codebases");
    assert(cy.get("h1").contains("Computational Model Library"));
  });

  it("should  be able to download a codebase", () => {
    cy.visit("/codebases");
    cy.get('[data-cy="codebase-search-result"]').first().find("a").first().click();
    cy.get('button.btn.btn-primary.my-1.w-100[rel="nofollow"]').click();
    cy.get("#form-field-industry").select("College/University");
    cy.get("#form-field-affiliation").type("Arizona State University{enter}", {
      force: true,
    });
    cy.get("#form-field-reason").select("Research");
    cy.get(
      'button[type="submit"][form="download-request-form"].btn.btn-success'
    ).click();
    cy.wait(1000)
  });

  it("should be able to upload a codebase", function() {
    cy.fixture('codebase/data.json').then((data) => {
      const codebase = data.codebases[0];
      const user = data.users[0];

      loginBeforeEach(user.username, user.password);
      cy.visit("/codebases");
      assert(cy.get("h1").contains("Computational Model Library"));
      cy.contains("Publish a model").click();
      cy.get('[data-cy="codebase title"]').type(codebase.title);
      cy.get('[data-cy="codebase description"]').type(codebase.description);
      cy.get('[data-cy="codebase replication-text"]').type(codebase['replication-text']);
      cy.get('[data-cy="codebase associated publications"]').type(codebase['associated-publications']);
      cy.get('[data-cy="codebase references"]').type(codebase.references);
      cy.get('[data-cy="next"]').click();

      //add images
      cy.get('[data-cy="add image"]').click();
      cy.get('[data-cy="upload-image"]')
        .first()
        .selectFile("cypress/fixtures/codebase/codebasetestimage.png", { force: true });
      cy.get('button.btn.btn-outline-gray[data-bs-dismiss="modal"]').first().click({ force: true });
      cy.get('button.btn.btn-outline-gray[data-bs-dismiss="modal"]').should("be.visible").and("not.be.disabled").first().click({ force: true });
      cy.wait(1000);
      cy.get("body").click(0, 0);
      cy.get("body").click(0, 0);

      //add images
      cy.get('[data-cy="upload-code"]')
        .first()
        .selectFile("cypress/fixtures/codebase/testCodebase.zip", { force: true });
      cy.get('[data-cy="upload-docs"]')
        .first()
        .selectFile("cypress/fixtures/codebase/testNarrativeDocumentation.txt", { force: true });
      cy.get('[data-cy="upload-data"]')
        .first()
        .selectFile("cypress/fixtures/codebase/testUploadData.txt", { force: true });
      cy.get('[data-cy="upload-results"]')
        .first()
        .selectFile("cypress/fixtures/codebase/testSimulationOutput.txt", { force: true });

      cy.get('[data-cy="add metadata"]').click();
      cy.get('[data-cy="release-notes"] textarea').type("Release notes");
      cy.get('[data-cy="embargo-end-date"]').click();
      cy.get('[data-cy="embargo-end-date"]').contains("29").click();
      cy.get('[data-cy="operating-system"] select').select("Operating System Independent");
      cy.get('[data-cy="software-frameworks"]').type("NetLogo {enter}");
      cy.get("body").click(0, 0);
      cy.get('[data-cy="programming-languages"]').type("Net Logo {enter}");
      cy.get("body").click(0, 0);
      cy.get('[data-cy="license"] .multiselect__select').click();
      cy.get('[data-cy="license"] .multiselect__element').contains("GPL-2.0").click();
      cy.get('[data-cy="save-and-continue"]').click();
      cy.get('button.btn.btn-danger[rel="nofollow"]').click();
      cy.get('button[type="submit"].btn.btn-danger[form="publish-form"]').click();
      cy.wait(2000);
    });
  });

  it("should verify that the codebase was uploaded correctly", function() {
    cy.fixture('codebase/data.json').then((data) => {
      const codebase = data.codebases[0];

      cy.visit("/codebases");
      cy.get('[data-cy="codebase-search-result"]').first().find("a").first().click();
      cy.contains(codebase.title).should('exist');
      cy.contains(codebase.description).should('exist');
      cy.contains(codebase['replication-text']).should('exist');
      cy.contains(codebase['associated-publications']).should('exist');
      cy.contains(codebase.references).should('exist');
    });
  })
});
