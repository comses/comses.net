import { loginBeforeEach } from "./setup.spec";
import "cypress-file-upload";


describe("Visit events page", () => {
    //EVENTS PAGE
  
    it("should visit the events page", () => {
      cy.visit("/events");
      assert(cy.get("h1").contains("Community Events"));
      cy.get(".card-body").first().find("a").first().click();
      assert(cy.get("h1").contains("Title"));
    });
  
    it("should be able to search for a specific event", () => {
      cy.visit("/events");
      cy.get('input[class="form-control"]').type(
        "Call for applications to organize a 2022 CECAM-Lorentz funded workshop on modeling"
      );
      cy.get("button.btn.btn-primary").click();
    });
  
    it("should be able to submit an event", () => {
      loginBeforeEach("test_user", "123456");
      cy.visit("/events");
      cy.get("#djHideToolBarButton").click();
      cy.get(".text-white").first().click({ force: true });
      cy.get('[data-cy="event title"]').type("Title");
      cy.get('[data-cy="event location"]').type("Location");
      cy.get('[data-cy="event start date"]').first().click(); //event start date
      cy.get('[data-cy="event start date"]').contains("22").click();
      cy.get('[data-cy="event end date"]').first().click(); //event end date
      cy.get('[data-cy="event end date"]').contains("27").click();
      cy.get('[data-cy="early registration deadline"]').first().click(); //early registration deadline
      cy.get('[data-cy="early registration deadline"]').contains("22").click();
      cy.get('[data-cy="registration deadline"]').first().click(); //registration deadline
      cy.get('[data-cy="registration deadline"]').contains("25").click();
      cy.get('[data-cy="submission deadline"]').first().click(); //submission deadline
      cy.get('[data-cy="submission deadline"]').contains("22").click();
      cy.get('[data-cy="description"]').type("Description");
      cy.get('[data-cy="summary"]').type("Summary");
      cy.get('[data-cy="external url"]').type("https://www.comses.net/");
      cy.get('[data-cy="create button"]').click();
    });
  
    it("should be able to verify event was submitted correctly", () => {
      cy.visit("/events");
      cy.get("#djHideToolBarButton").click();
      assert(cy.get("h1").contains("Community Events"));
      cy.get(".card-body").first().find("a").first().click();
      assert(cy.get("h1").contains("Title"));
      assert(cy.get("p").contains("Description"));
      assert(cy.get("p").contains("Location"));
    });
  });