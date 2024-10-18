import { loginBeforeEach } from "../support/setup";
import { getDataCy } from "../support/util";
import "cypress-file-upload";

//login
describe("Login", () => {
  it("should log into comses homepage with test user", function () {
    cy.fixture("data.json").then(data => {
      const user = data.users[0];
      loginBeforeEach(user.username, user.password);
    });
  });
});

describe("Visit codebases page", () => {
  //codebases PAGE

  it("should visit the codebases page", () => {
    cy.visit("/codebases");
    assert(cy.get("h1").contains("Computational Model Library"));
  });

  it("should be able to download a codebase", () => {
    cy.visit("/codebases");
    getDataCy("codebase-search-result").first().find("a").first().click();
    getDataCy("release-version").click();
    getDataCy("industry").find("select").select("College/University");
    cy.get('[data-cy="affiliation"] input').first().type("Arizona State University {enter}", {
      force: true,
    });
    cy.get('[data-cy="reason"] select').select("Research", { force: true });
    getDataCy("submit-download").click();
    cy.wait(1000);
  });

  it("should be able to upload a codebase", function () {
    cy.fixture("data.json").then(data => {
      const codebase = data.codebases[0];
      const user = data.users[0];

      loginBeforeEach(user.username, user.password);
      cy.visit("/codebases");
      assert(cy.get("h1").contains("Computational Model Library"));
      cy.contains("Publish a model").click();
      getDataCy("codebase-title").type(codebase.title);
      getDataCy("codebase-description").type(codebase.description);
      getDataCy("codebase-replication-text").type(codebase["replication-text"]);
      getDataCy("codebase-associated-publications").type(codebase["associated-publications"]);
      getDataCy("codebase-references").type(codebase.references);
      getDataCy("next").click();
      // make sure the release editor is initialized
      cy.wait(2000);
      //add images
      getDataCy("add-image").click();
      getDataCy("upload-image")
        .first()
        .selectFile("cypress/fixtures/codebase/codebasetestimage.png", { force: true });
      cy.wait(1000);
      cy.get("body").click(0, 0);
      cy.get("body").click(0, 0);

      //upload files
      getDataCy("upload-code")
        .first()
        .selectFile("cypress/fixtures/codebase/testCodebase.zip", { force: true });
      getDataCy("upload-docs")
        .first()
        .selectFile("cypress/fixtures/codebase/testNarrativeDocumentation.txt", { force: true });
      getDataCy("upload-data")
        .first()
        .selectFile("cypress/fixtures/codebase/testUploadData.txt", { force: true });
      getDataCy("upload-results")
        .first()
        .selectFile("cypress/fixtures/codebase/testSimulationOutput.txt", { force: true });

      getDataCy("add-metadata").click();
      getDataCy("release-notes").type("Release notes");
      getDataCy("embargo-end-date").click();
      getDataCy("embargo-end-date").contains("29").click();
      getDataCy("operating-system").find("select").select("Operating System Independent");
      getDataCy("software-frameworks").type("NetLogo {enter}");
      cy.get("body").click(0, 0);
      getDataCy("programming-languages").type("Net Logo {enter}");
      cy.get("body").click(0, 0);
      getDataCy("license").click();
      getDataCy("license").within(() => {
        cy.contains("GPL-2.0").click();
      });
      getDataCy("save-and-continue").click();
      cy.contains("button", "Publish").click();
      getDataCy("publish").click();
      cy.wait(2000);
    });
  });

  it("should verify that the codebase was uploaded correctly", function () {
    cy.fixture("data.json").then(data => {
      const codebase = data.codebases[0];
      cy.visit("/codebases");
      getDataCy("codebase-search-result").first().find("a").first().click();
      cy.contains(codebase.title).should("exist");
      cy.contains(codebase.description).should("exist");
      cy.contains(codebase["replication-text"]).should("exist");
      cy.contains(codebase["associated-publications"]).should("exist");
      cy.contains(codebase.references).should("exist");
    });
  });
});
