import { loginBeforeEach } from "./setup.spec";
import "cypress-file-upload";

describe("Visit jobs page", () => {
    //JOBS PAGE
  
    it("should visit the jobs page", () => {
      cy.visit("/jobs");
      assert(cy.get("h1").contains("Jobs & Appointments"));
    });
  
    it("should be able to submit a job posting", () => {
      loginBeforeEach("test_user", "123456");
      cy.visit("/jobs");
      cy.get(".text-white").first().click({ force: true });
      cy.get('[data-cy="job title"]').type("Job Title");
      cy.get('[data-cy="job description"]').type("Job Description");
      cy.get('[data-cy="job summary"]').type("Job Summary");
      cy.get('[data-cy="external url"]').type("https://www.comses.net/");
      cy.get('[data-cy="application deadline"]').first().click();
      cy.get('[data-cy="application deadline"]').contains("29").click();
      cy.get('[data-cy="create button"]').click();
      cy.wait(2000)
    });
  
    it("should be able to verify job was submitted correctly", () => {
      cy.visit("/jobs");
      assert(cy.get("h1").contains("Jobs & Appointments"));
      cy.get(".card-body").first().find("a").first().click();
      assert(cy.get("h1").contains("Job Title"));
      assert(cy.get("p").contains("Job Description"));
    });
  });
  