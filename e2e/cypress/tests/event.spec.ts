import { loginBeforeEach } from "./setup.spec";
import "cypress-file-upload";


describe("Visit events page", () => {
    //EVENTS PAGE
  
    it("should visit the events page", () => {
      cy.visit("/events");
      assert(cy.get("h1").contains("Community Events"));
      cy.get(".card-body").first().find("a").first().click();
      assert(cy.get("h1").contains("25th International Congress on Environmental Modelling and Software"));
    });
  
    it("should be able to search for a specific event", () => {
      cy.visit("/events");
      cy.get('input[class="form-control"]').type(
        "Call for applications to organize a 2022 CECAM-Lorentz funded workshop on modeling"
      );
      cy.get("button.btn.btn-primary").click();
    });
  
    it("should be able to submit an event", function() {
      cy.fixture('codebase/data.json').then((data) => {
        const user = data.users[0];
        const event = data.events[0];
  
        loginBeforeEach(user.username, user.password);
  
        cy.visit("/events");
        cy.get(".text-white").first().click({ force: true });
        cy.get('[data-cy="event title"]').type(event.title);
        cy.get('[data-cy="event location"]').type(event.location);
        cy.get('[data-cy="event start date"]').first().click();
        cy.get('[data-cy="event start date"]').contains(event['start-date']).click();
        cy.get('[data-cy="event end date"]').first().click();
        cy.get('[data-cy="event end date"]').contains(event['end-date']).click();
        cy.get('[data-cy="early registration deadline"]').first().click();
        cy.get('[data-cy="early registration deadline"]').contains(event['early-registration-deadline']).click();
        cy.get('[data-cy="registration deadline"]').first().click();
        cy.get('[data-cy="registration deadline"]').contains(event['registration-deadline']).click();
        cy.get('[data-cy="submission deadline"]').first().click();
        cy.get('[data-cy="submission deadline"]').contains(event['submission-deadline']).click();
        cy.get('[data-cy="description"]').type(event.description);
        cy.get('[data-cy="summary"]').type(event.summary);
        cy.get('[data-cy="external url"]').type(event['external-url']);
        cy.get('[data-cy="create button"]').click();
        cy.wait(2000);
      });
    });
  
    it("should be able to verify event was submitted correctly", function() {
      cy.fixture('codebase/data.json').then((data) => {
        const event = data.events[0];
  
        cy.visit("/events");
        assert(cy.get("h1").contains("Community Events"));
        cy.get(".card-body").first().find("a").first().click();
        assert(cy.get("h1").contains(event.title));
        assert(cy.get("p").contains(event.description));
        assert(cy.get("p").contains(event.location));
      });
    });
  });