import { loginBeforeEach } from "../support/setup";
import { getDataCy } from "../support/util";
import "cypress-file-upload";

//login
describe("User tests", () => {
  it("should visit the users page and update the profile", function () {
    cy.fixture("data.json").then(data => {
      const adminUser = data.users.find(user => user.username === "admin_user");
      const newUser = data.users.find(user => user["first-name"] && user["last-name"]);
      loginBeforeEach(adminUser.username, adminUser.password);
      cy.visit("/users");
      cy.contains("div", "My profile").click();
      cy.contains("a", "Edit Profile").click();
      getDataCy("first name").find("input").clear().type(newUser["first-name"]);
      getDataCy("last name").find("input").clear().type(newUser["last-name"]);
      getDataCy("submit").click();
      cy.contains(`${newUser["first-name"]} ${newUser["last-name"]}`).should("exist");
    });
  });
});
