import { loginBeforeEach } from "./setup.spec";
import "cypress-file-upload";

//login
describe("Login", () => {
  it("should log into comses homepage with test user", () => {
    loginBeforeEach("test_user", "123456");
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
    cy.get(".search-result").first().find("a").first().click();
    cy.get("#djHideToolBarButton").click();
    cy.get('button.btn.btn-primary.my-1.w-100[rel="nofollow"]').click();
    cy.get("#form-field-industry").select("College/University");
    cy.get("#form-field-affiliation").type("Arizona State University{enter}", {
      force: true,
    });
    cy.get("#form-field-reason").select("Research");
    cy.get(
      'button[type="submit"][form="download-request-form"].btn.btn-success'
    ).click();
  });

  it("should be able to upload a codebase", () => {
    loginBeforeEach("test_user", "123456");
    cy.visit("/codebases");
    assert(cy.get("h1").contains("Computational Model Library"));
    cy.get("#djHideToolBarButton").click();
    cy.contains("Publish a model").click();
    cy.get('[data-cy="codebase title"]').type("Codebase Title");
    cy.get('[data-cy="codebase description"]').type("Codebase Description");
    cy.get('[data-cy="codebase replication-text"]').type(
      "Codebase Replication Text"
    );
    cy.get('[data-cy="codebase associated publications"]').type(
      "Codebase Associated Publications"
    );
    cy.get('[data-cy="codebase references"]').type("Codebase References");
    cy.get('[data-cy="next"]').click();
    //add images
    cy.get('[data-cy="add image"]').click(); //add image
    cy.get('[data-cy="upload-image"]')
      .first()
      .selectFile("cypress/fixtures/codebase/codebasetestimage.png", {
        force: true,
      });
    cy.get('button.btn.btn-outline-gray[data-bs-dismiss="modal"]')
      .get("button")
      .first()
      .click({ force: true });
    cy.get('button.btn.btn-outline-gray[data-bs-dismiss="modal"]')
      .should("be.visible")
      .and("not.be.disabled")
      .first()
      .click({ force: true });
    cy.get("body").click(0, 0);
    cy.get("body").click(0, 0); //FIX: find a more precise way of closing the image upload modal

    //add source code files
    cy.get('[data-cy="upload-code"]')
      .first()
      .selectFile("cypress/fixtures/codebase/testSourceCode.txt", {
        force: true,
      });
    cy.get('[data-cy="upload-docs"]')
      .first()
      .selectFile("cypress/fixtures/codebase/testNarrativeDocumentation.txt", {
        force: true,
      });
    cy.get('[data-cy="upload-data"]')
      .first()
      .selectFile("cypress/fixtures/codebase/testUploadData.txt", {
        force: true,
      });
    cy.get('[data-cy="upload-results"]')
      .first()
      .selectFile("cypress/fixtures/codebase/testSimulationOutput.txt", {
        force: true,
      });
    cy.get('[data-cy="add metadata"]').click();
    cy.get('[data-cy="release-notes"] textarea').type("Release notes");
    cy.get('[data-cy="embargo-end-date"]').click();
    cy.get('[data-cy="embargo-end-date"]').contains("29").click();
    cy.get('[data-cy="operating-system"] select').select(
      "Operating System Independent"
    );
    cy.get('[data-cy="software-frameworks"]').type("NetLogo {enter} ");
    cy.get("body").click(0, 0);
    cy.get('[data-cy="programming-languages"').type("Net Logo {enter}");
    cy.get("body").click(0, 0);
    cy.get('[data-cy="license"] .multiselect__select').click();
    cy.get('[data-cy="license"] .multiselect__element')
      .contains("GPL-2.0")
      .click();
    cy.get('[data-cy="save-and-continue"]').click();
    cy.get('button.btn.btn-danger[rel="nofollow"]').click();
    cy.get('button[type="submit"].btn.btn-danger[form="publish-form"]').click();
  });

  it("should verify that the codebase was uploaded correctly", () => {
    cy.visit("/codebases");
    cy.get(".search-result").first().find("a").first().click();
    assert(cy.get("h1").contains("Codebase Title"));
    assert(cy.get("p").contains("Codebase Description"));
    assert(cy.get("p").contains("Codebase Replication Text"));
    assert(cy.get("p").contains("Codebase Associated Publications"));
    assert(cy.get("p").contains("Codebase References"));

  })
});