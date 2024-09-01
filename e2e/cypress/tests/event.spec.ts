import { loginBeforeEach } from "../support/setup";
import { getDataCy } from "../support/util";
import "cypress-file-upload";

describe("Visit events page", () => {
  //EVENTS PAGE

  it("should visit the events page", () => {
    cy.visit("/events");
    assert(cy.get("h1").contains("Community Events"));
    getDataCy("event-result").first().find("a").first().click();
    assert(
      cy.get("h1").contains("25th International Congress on Environmental Modelling and Software")
    );
  });

  it("should be able to search for a specific event", () => {
    cy.visit("/events");
    getDataCy("search-bar").type(
      "Call for applications to organize a 2022 CECAM-Lorentz funded workshop on modeling"
    );
    getDataCy("search-button").click();
  });

  it("should be able to submit an event", function () {
    cy.fixture("data.json").then(data => {
      const user = data.users[0];
      const event = data.events[0];
      loginBeforeEach(user.username, user.password);
      cy.visit("/events");
      cy.contains("Submit an event").click();
      getDataCy("event-title").type(event.title);
      getDataCy("event-location").type(event.location);
      getDataCy("event-start-date").first().click();
      getDataCy("event-start-date").contains(event["start-date"]).click();
      getDataCy("event-end-date").first().click();
      getDataCy("event-end-date").contains(event["end-date"]).click();
      getDataCy("early-registration-deadline").first().click();
      getDataCy("early-registration-deadline")
        .contains(event["early-registration-deadline"])
        .click();
      getDataCy("registration-deadline").first().click();
      getDataCy("registration-deadline").contains(event["registration-deadline"]).click();
      getDataCy("submission-deadline").first().click();
      getDataCy("submission-deadline").contains(event["submission-deadline"]).click();
      getDataCy("description").type(event.description);
      getDataCy("summary").type(event.summary);
      getDataCy("external-url").type(event["external-url"]);
      getDataCy("create-button").click();
      cy.wait(2000);
    });
  });

  it("should be able to verify event was submitted correctly", function () {
    cy.fixture("data.json").then(data => {
      const event = data.events[0];
      cy.visit("/events");
      assert(cy.get("h1").contains("Community Events"));
      getDataCy("event-result").first().find("a").first().click();
      assert(cy.get("h1").contains(event.title));
      assert(cy.get("p").contains(event.description));
      assert(cy.get("p").contains(event.location));
    });
  });
});
