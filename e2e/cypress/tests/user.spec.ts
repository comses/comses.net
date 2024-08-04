import { loginBeforeEach } from "./setup.spec";
import "cypress-file-upload";

//login
describe("User tests", () => {
    it("should visit the users page and update the profile", function() {
    cy.fixture('codebase/data.json').then((data) => {
      const adminUser = data.users.find(user => user.username === "admin_user");
      const newUser = data.users.find(user => user["first-name"] && user["last-name"]);
      loginBeforeEach(adminUser.username, adminUser.password);
      cy.visit("/users");
      cy.contains('div', 'My profile').click();
      cy.contains('a', 'Edit Profile').click();
      cy.get('#form-field-givenName').clear();
      cy.get('[data-cy="first name"]').type(newUser["first-name"]);
      cy.get('#form-field-familyName').clear();
      cy.get('[data-cy="last name"]').type(newUser["last-name"]);
      cy.get('[data-cy="submit"]').click();
      cy.contains(`${newUser["first-name"]} ${newUser["last-name"]}`).should('exist');
    });
  });
  });

