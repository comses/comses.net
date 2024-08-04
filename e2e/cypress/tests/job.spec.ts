import { loginBeforeEach } from "./setup.spec";
import "cypress-file-upload";

describe("Visit jobs page", () => {
    //JOBS PAGE
  
    it("should visit the jobs page", () => {
      cy.visit("/jobs");
      assert(cy.get("h1").contains("Jobs & Appointments"));
    });
  
    it("should be able to submit a job posting", function() {
      cy.fixture('codebase/data.json').then((data) => {
        const user = data.users[0];
        const job = data.jobs[0];
        loginBeforeEach(user.username, user.password);
        cy.visit("/jobs");
        cy.get(".text-white").first().click({ force: true });
        cy.get('[data-cy="job title"]').type(job.title);
        cy.get('[data-cy="job description"]').type(job.description);
        cy.get('[data-cy="job summary"]').type(job.summary);
        cy.get('[data-cy="external url"]').type(job['external-url']);
        cy.get('[data-cy="application deadline"]').first().click();
        cy.get('[data-cy="application deadline"]').contains(job['application-deadline']).click();
        cy.get('[data-cy="create button"]').click();
        cy.wait(2000);
      });
    });
  
    it("should be able to verify job was submitted correctly", function() {
      cy.fixture('codebase/data.json').then((data) => {
        const job = data.jobs[0];
  
        cy.visit("/jobs");
        assert(cy.get("h1").contains("Jobs & Appointments"));
        cy.get(".card-body").first().find("a").first().click();
  
        assert(cy.get("h1").contains(job.title));
        assert(cy.get("p").contains(job.description));
      });
    });
  });
  