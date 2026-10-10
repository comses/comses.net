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
      getDataCy("publish").contains("Publish").click();
      getDataCy("codebase-title").type(codebase.title);
      getDataCy("codebase-description").type(codebase.description);
      getDataCy("codebase-replication-text").type(codebase["replication-text"]);
      getDataCy("codebase-associated-publications").type(codebase["associated-publications"]);
      getDataCy("codebase-references").type(codebase.references);
      getDataCy("next").click();
      // make sure the release editor is initialized
      cy.wait(2000);
      // add media (images + optional YouTube)
      getDataCy("add-media").click();
      getDataCy("upload-image")
        .first()
        .selectFile("cypress/fixtures/codebase/codebasetestimage.png", { force: true });
      cy.wait(1000);
      cy.get("body").click(0, 0);
      cy.get("body").click(0, 0);

      getDataCy("file-guidance-code").should("have.attr", "aria-selected", "true");
      getDataCy("file-guidance-docs").trigger("pointerenter", { pointerType: "mouse" });
      getDataCy("file-guidance-docs").should("have.attr", "aria-selected", "false");
      getDataCy("file-guidance-docs").click();
      cy.get("#file-guidance-content-docs").should("be.visible").and("contain", "ODD Protocol");
      cy.get("#file-guidance-content-code").should("not.be.visible");
      getDataCy("file-guidance-metadata").click();
      cy.get("#file-guidance-content-metadata")
        .should("be.visible")
        .and("contain", "CITATION.cff")
        .and("contain", "codemeta.json")
        .and("contain", "LICENSE");
      getDataCy("file-guidance-metadata").trigger("keydown", { key: "Home" });
      getDataCy("file-guidance-code").should("be.focused").and("have.attr", "aria-selected", "true");

      cy.intercept("POST", "**/files/package/").as("uploadPackage");
      getDataCy("dropzone-package").selectFile([
        "cypress/fixtures/codebase/testSourceCode.txt",
        "cypress/fixtures/codebase/testNarrativeDocumentation.txt",
        "cypress/fixtures/codebase/testUploadData.txt",
        "cypress/fixtures/codebase/testSimulationOutput.txt",
      ], { action: "drag-drop" });
      cy.wait(["@uploadPackage", "@uploadPackage", "@uploadPackage", "@uploadPackage"]);
      getDataCy("upload-status-package").should("contain", "4 of 4 files uploaded");
      getDataCy("dropzone-package").should("not.be.disabled");
      cy.intercept("POST", "**/update_category/").as("categorize");
      cy.get('[data-file-path="testNarrativeDocumentation.txt"]').select("docs");
      cy.wait("@categorize");
      cy.get('[data-file-path="testUploadData.txt"]').select("data");
      cy.wait("@categorize");
      cy.get('[data-file-path="testSimulationOutput.txt"]').select("results");
      cy.wait("@categorize");
      cy.reload();
      cy.get('[data-file-path="testNarrativeDocumentation.txt"]').should("have.value", "docs");
      cy.get('[data-file-path="testUploadData.txt"]').should("have.value", "data");

      getDataCy("add-metadata").click();
      getDataCy("release-notes").type("Release notes");
      getDataCy("embargo-end-date").click();
      getDataCy("embargo-end-date").contains("29").click();
      getDataCy("operating-system").find("select").select("Operating System Independent");
      getDataCy("software-frameworks").type("NetLogo {enter}");
      cy.get("body").click(0, 0);
      getDataCy("programming-languages").find("input[type=\"checkbox\"]").check();
      getDataCy("programming-languages").type("Netlogo {enter}");
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
