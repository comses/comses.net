import { loginBeforeEach } from "./setup.spec";
import 'cypress-file-upload'

//login
/*
describe("Login", () => {
  it("should log into comses homepage with test user", () => {
    loginBeforeEach('testuser', '123456');
    assert(cy.get("h1").contains("A growing collection of resources for computational model-based science."));
  })
})

//visit various pages
describe("Visit about page", () => { //ABOUT PAGE
  it("should visit the about page after logging in", () =>{
    cy.visit("/about");
    assert(cy.get("h1").contains("About"));
    assert(cy.get("h1").contains("About CoMSES Net / OpenABM"));
  })

  it("should visit the about/people page", () =>{
    cy.visit("/about/people");
    assert(cy.get("h1").contains("People"));
    cy.get('.card').first().find('a').first().click();
    cy.get('.nav-item').eq(9).find('a').click();
    assert(cy.get("p").contains("Because tree travel seat visit senior these go. Carry bring front stuff tend. Mother field sea report culture least. Produce appear after participant lose leg."));
    cy.get('.nav-item').eq(10).find('a').click();
    assert(cy.get("p").contains("No submitted codebases."));
    cy.get('.nav-item').eq(11).find('a').click();
    assert(cy.get("p").contains("Under development."));
  })
    
  it("should visit the about/community page", () =>{
    cy.visit("/about/community");
    assert(cy.get("h1").contains("Welcome to the CoMSES Net Community"));
  })
    
  it("should visit the about/faq page", () =>{
    cy.visit("/about/faq");
    assert(cy.get("h1").contains("Frequently Asked Questions"));
    cy.contains('h2', 'Agent-based Modeling Questions').parent() // Move up to the container of the h2
    .find('.btn-link').first() // Find the button to toggle the accordion
    .click();
    assert(cy.get("p").contains("Models are tools for communication, education, exploration and experimentation. Models are not holy tools for prediction, especially not for non-linear systems. Unfortunately, there is a lot of misunderstanding about models. People who are not very familiar with them have sometimes high expectations of the details that are included. A common critique of non-modelers is that more details need to be included. But more details might only make the model less useful for exploration of the parameter space. The goal is to make “the models as simple as possible, but no simpler than that”. One confuses often the use of a model with a description of the real systems."));
  })
    
  it("should visit the about/contact", () =>{
    cy.visit("/about/contact");
    assert(cy.get("h1").contains("Contact Us"));
    //fill out contact us form
    cy.get('input[name="name"]').type("John Doe");
    cy.get('input[name="email"]').type("johndoe@gmail.com");
    cy.get('input[name="subject_text"]').type("subject text");
    cy.get('#id_body').type("complaint blah blah");
  })
})

describe("Visit education page", () =>{ //EDUCATION PAGE
  it("should visit the Responsible Practices for Scientific Software page", () =>{
    cy.visit("/education");
    assert(cy.get("h1").contains("Training Modules"));
    cy.get('.card-body').eq(0).find('.stretched-link').click({force: true});
    assert(cy.get("h1").contains("Responsible Practices for Scientific Software"));
  })

  it("should visit the Introduction to Git and GitHub page", () =>{
    cy.visit('/education');
    assert(cy.get("h1").contains("Training Modules"));
    cy.get('.card-body').eq(1).find('.stretched-link').click({force: true});
    assert(cy.get("h1").contains("Introduction to Git and GitHub"));
  })
})

describe("Visit events page", () =>{ //EVENTS PAGE

  it("should visit the events page", () =>{
    cy.visit("/events");
    assert(cy.get("h1").contains("Community Events"));
    cy.get('.card-body').first().find('a').first().click();
    assert(cy.get("h1").contains("Title"));
    
  })
  
  it("should be able to search for a specific event", () =>{
    cy.visit("/events");
    cy.get('input[class="form-control"]').type("Call for applications to organize a 2022 CECAM-Lorentz funded workshop on modeling");
    cy.get('button.btn.btn-primary').click();
  })

  it("should be able to submit an event", () =>{
    loginBeforeEach('testuser', '123456');
    cy.visit("/events");
    cy.get('#djHideToolBarButton').click();
    cy.get('.text-white').first().click({force:true});
    cy.get('input[name="title"]').type("Title");
    cy.get('input[name="location"]').type("Location");
    cy.get('input[class="dp__pointer dp__input_readonly dp__input dp__input_reg"]').first().click(); //event start date
    cy.get('.dp__cell_inner.dp__pointer.dp__date_hover').contains('22').click();
    cy.get('input[class="dp__pointer dp__input_readonly dp__input dp__input_reg"]').eq(1).click(); //event end date
    cy.get('.dp__cell_inner.dp__pointer.dp__date_hover').contains('27').click();
    cy.get('input[class="dp__pointer dp__input_readonly dp__input dp__input_reg"]').eq(2).click(); //early registration deadline
    cy.get('.dp__cell_inner.dp__pointer.dp__date_hover').contains('22').click();
    cy.get('input[class="dp__pointer dp__input_readonly dp__input dp__input_reg"]').eq(3).click(); //registration deadline
    cy.get('.dp__cell_inner.dp__pointer.dp__date_hover').contains('25').click();
    cy.get('input[class="dp__pointer dp__input_readonly dp__input dp__input_reg"]').eq(4).click(); //submission deadline
    cy.get('.dp__cell_inner.dp__pointer.dp__date_hover').contains('22').click();
    cy.get('#form-field-description').type('Description');
    cy.get('#form-field-summary').type('Summary');
    cy.get('#form-field-externalUrl').type('https://www.comses.net/');
    cy.contains('button.btn.btn-primary', 'Create').click();
  })

  it("should be able to verify event was submitted correctly", () =>{
    cy.visit("/events");
    cy.get('#djHideToolBarButton').click();
    assert(cy.get("h1").contains("Community Events"));
    cy.get('.card-body').first().find('a').first().click();
    assert(cy.get("h1").contains("Title"));
    assert(cy.get("p").contains("Description"));
    assert(cy.get("p").contains("Location"));
  })
  
})

describe("Visit jobs page", () =>{ //JOBS PAGE

  it("should visit the events page", () =>{
    cy.visit("/jobs");
    assert(cy.get("h1").contains("Jobs & Appointments"));
  })

  it("should be able to submit a job posting", () =>{
    loginBeforeEach('testuser', '123456');
    cy.visit("/jobs");
    cy.get('#djHideToolBarButton').click();
    cy.get('.text-white').first().click({force:true});
    cy.get('input[name="title"]').type("Job Title");
    cy.get('#form-field-description').type('Job Description');
    cy.get('#form-field-summary').type('Job Summary');
    cy.get('#form-field-externalUrl').type('https://www.comses.net/');
    cy.get('input[class="dp__pointer dp__input_readonly dp__input dp__input_reg"]').first().click(); //event start date
    cy.get('.dp__cell_inner.dp__pointer.dp__date_hover').contains('29').click();
    cy.contains('button.btn.btn-primary', 'Create').click();
  })

  it("should be able to verify event was submitted correctly", () =>{
    cy.visit("/jobs");
    cy.get('#djHideToolBarButton').click();
    assert(cy.get("h1").contains("Jobs & Appointments"));
    cy.get('.card-body').first().find('a').first().click();
    assert(cy.get("h1").contains("Job Title"));
    assert(cy.get("p").contains("Job Description"));
  })
  
})

*/


describe("Visit codebases page", () =>{ //codebases PAGE

  it("should visit the codebases page", () =>{
    cy.visit("/codebases");
    assert(cy.get("h1").contains("Computational Model Library"));
  })

  it("should  be able to download a codebase", () => {
    cy.visit("/codebases");
    cy.get('.search-result').first().find('a').first().click();
    cy.get('#djHideToolBarButton').click();
    cy.get('button.btn.btn-primary.my-1.w-100[rel="nofollow"]').click();
    cy.get('#form-field-industry').select('College/University');
    cy.get('#form-field-affiliation').type("Arizona State University{enter}", {force: true});
    cy.get('#form-field-reason').select('Research');
    cy.get('button[type="submit"][form="download-request-form"].btn.btn-success').click();
  })

  it("should be able to upload a codebase", () =>{
    loginBeforeEach('test_user', '123456');
    cy.visit("/codebases");
    assert(cy.get("h1").contains("Computational Model Library"));
    cy.get('#djHideToolBarButton').click();
    cy.contains('Publish a model').click();
    cy.get('[data-cy="codebase title"]').type("Codebase Title");
    cy.get('[data-cy="codebase description"]').type("Codebase Description");
    cy.get('[data-cy="codebase replication-text"]').type("Codebase Replication Text");
    cy.get('[data-cy="codebase associated publications"]').type("Codebase Associated Publications");
    cy.get('[data-cy="codebase references"]').type("Codebase References");
    cy.get('[data-cy="next"]').click();
    //add images
    cy.get('[data-cy="add image"]').click(); //add image
    cy.get('[data-cy="upload-image"]').first().selectFile('cypress/fixtures/codebase/codebasetestimage.png', {force: true});
      cy.get('button.btn.btn-outline-gray[data-bs-dismiss="modal"]').get("button").first().click( {force: true} );
      cy.get('button.btn.btn-outline-gray[data-bs-dismiss="modal"]')
      .should('be.visible')
      .and('not.be.disabled')
      .first().
      click( {force: true} );
      cy.get('body').click(0, 0);
    cy.get('body').click(0, 0); //FIX: find a more precise way of closing the image upload modal 

    //add source code files
    cy.get('[data-cy="upload-code"]').first().selectFile('cypress/fixtures/codebase/testSourceCode.txt', {force: true});
    cy.get('[data-cy="upload-docs"]').first().selectFile('cypress/fixtures/codebase/testNarrativeDocumentation.txt', {force: true});
    cy.get('[data-cy="upload-data"]').first().selectFile('cypress/fixtures/codebase/testUploadData.txt', {force: true});
    cy.get('[data-cy="upload-results"]').first().selectFile('cypress/fixtures/codebase/testSimulationOutput.txt', {force: true});
    cy.get('[data-cy="add metadata"]').click();
    cy.get('[data-cy="release-notes"] textarea').type("Release notes");
    cy.get('[data-cy="embargo-end-date"]').click();
    cy.get('[data-cy="embargo-end-date"]').contains('29').click();
    cy.get('[data-cy="operating-system"] select').select('Operating System Independent');
    cy.get('[data-cy="software-frameworks"]').type("NetLogo {enter} ");
    cy.get('body').click(0, 0);
    cy.get('[data-cy="programming-languages"').type("Net Logo {enter}");
    cy.get('body').click(0, 0);
    cy.get('[data-cy="license"] .multiselect__select').click();
    cy.get('[data-cy="license"] .multiselect__element').contains('GPL-2.0').click();
    cy.get('[data-cy="save-and-continue"]').click();
    cy.get('button.btn.btn-danger[rel="nofollow"]').click();
    cy.get('button[type="submit"].btn.btn-danger[form="publish-form"]').click();







    







  })
  
})

