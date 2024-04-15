//contains setup function for smoke tests
export const loginBeforeEach = (username, password) => {
    cy.visit('/accounts/login/?next=/')
    assert(cy.get("h1").contains("Sign In")); //simply goes to sign in page
    cy.get('input[name="login"]').type(username)
    cy.get('input[name="password"]').type(password)
    cy.contains('button', 'Sign In').click();
}