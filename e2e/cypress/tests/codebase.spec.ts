import { loginBeforeEach } from "./setup.spec";
import 'cypress-file-upload'

//login
describe("Login", () => {
  it("should log into comses homepage with test user", () => {
    loginBeforeEach('testuser', '123456');
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
    loginBeforeEach('test_user', '123456');
    cy.visit("/events");
    cy.get('#djHideToolBarButton').click();
    cy.get('.text-white').first().click({force:true});
    cy.get('[data-cy="event title"]').type("Title");
    cy.get('[data-cy="event location"]').type("Location");
    cy.get('[data-cy="event start date"]').first().click(); //event start date
    cy.get('[data-cy="event start date"]').contains('22').click();
    cy.get('[data-cy="event end date"]').first().click(); //event end date
    cy.get('[data-cy="event end date"]').contains('27').click();
    cy.get('[data-cy="early registration deadline"]').first().click(); //early registration deadline
    cy.get('[data-cy="early registration deadline"]').contains('22').click();
    cy.get('[data-cy="registration deadline"]').first().click(); //registration deadline
    cy.get('[data-cy="registration deadline"]').contains('25').click();
    cy.get('[data-cy="submission deadline"]').first().click(); //submission deadline
    cy.get('[data-cy="submission deadline"]').contains('22').click();
    cy.get('[data-cy="description"]').type('Description');
    cy.get('[data-cy="summary"]').type('Summary');
    cy.get('[data-cy="external url"]').type('https://www.comses.net/');
    cy.get('[data-cy="create button"]').click();
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

  it("should visit the jobs page", () =>{
    cy.visit("/jobs");
    assert(cy.get("h1").contains("Jobs & Appointments"));
  })

  it("should be able to submit a job posting", () =>{
    loginBeforeEach('test_user', '123456');
    cy.visit("/jobs");
    cy.get('#djHideToolBarButton').click();
    cy.get('.text-white').first().click({force:true});
    cy.get('[data-cy="job title"]').type("Job Title");
    cy.get('[data-cy="job description"]').type('Job Description');
    cy.get('[data-cy="job summary"]').type('Job Summary');
    cy.get('[data-cy="external url"]').type('https://www.comses.net/');
    cy.get('[data-cy="application deadline"]').first().click();
    cy.get('[data-cy="application deadline"]').contains('29').click();
    cy.get('[data-cy="create button"]').click();
  })

  it("should be able to verify job was submitted correctly", () =>{
    cy.visit("/jobs");
    cy.get('#djHideToolBarButton').click();
    assert(cy.get("h1").contains("Jobs & Appointments"));
    cy.get('.card-body').first().find('a').first().click();
    assert(cy.get("h1").contains("Job Title"));
    assert(cy.get("p").contains("Job Description"));
  })
  
})

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

