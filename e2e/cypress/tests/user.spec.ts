import { loginBeforeEach } from "./setup.spec";
import "cypress-file-upload";

//login
describe("User tests", () => {
    it("should visit the users page", () => {
        loginBeforeEach("admin_user", "123456");
        cy.visit("/users");
        cy.contains('div', 'My profile').click();
        cy.contains('a', 'Edit Profile').click();
        cy.get('#form-field-givenName').clear()
        cy.get('[data-cy="first name"]').type("New first name");
        cy.get('#form-field-familyName').clear()
        cy.get('[data-cy="last name"]').type("New last name");
        cy.get('[data-cy="submit"]').click();
        assert(cy.get("h4").contains("New first name New last name"));
        
    });
  });