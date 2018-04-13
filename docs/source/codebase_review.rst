Codebase Review Workflow
========================

Review workflow for the CoMSES computational model library that enables authors to submit a specific codebase version for a peer review certification process similar in spirit to PlOS One, i.e., a structural / software integrity review that checks:

1. Does the codebase have accompanying narrative documentation?
2. Is the code clean / well-written / well-commented? (formatted properly, etc.)
3. Can you run the model with the provided instructions?

Each of these questions has two other fields associated with it:

1. a select box "Does not meet standards", "Partially meets standards", "Fully meets standards"
2. Free form notes field

At the end, a final recommendation:
1. Do not certify / deny
2. Revise and resubmit
3. Certify / accept

Review statuses
---------------

Reviews have the following statuses:

1. Review requested (editor needs to invite a peer reviewer)
2. Reviewers invited (editor sent emails to candidate peer reviewers who will accept / decline the request to review the given codebase)
3. Reviewer accepted (candidate peer reviewer will perform the codebase review, timer is set to periodically remind the reviewer and after a certain amount of time, the editor also needs to be notified)
4. Reviewer declined (editor action required, go back to step 2 to invite candidate peer reviewers)
5. Review completed (peer reviewer has filled out the codebase review form and submit a final recommendation to be taken by the editor)
6. The editor has the final say whether or not to accept the reviewer's recommendation and will manually change the status of the review to `Accepted, Denied, or Revise/Resubmit`
7. If revise / resubmit, the author can make changes to their codebase version and then resubmit it for review, which brings it back to Step 1 (with the history of changes preserved).

Sample workflow
---------------

* Codebase submitter requests a review for a specific codebase release version
* Review shows up in an admin / editor visible queue with the appropriate status
* Review manager / admin selects a review in the New Review Requests queue and selects (one or more) candidate reviewer(s) to invite via customized form-letter email
* Candidate reviewers can be a Full CoMSES Member, any user that has published a model in the Model Library, or an outside individual not registered on the site. (All reviewers who accept the model review will gain full CoMSES member status if they do not already possess that status.)
* Search interface to find candidate reviewers (probably by tags related to a user, either via the profile or past codebase release submissions)
* Candidate reviewer listings should also show review metadata many times they've been invited, accepted, or declined to review.
* Outside candidates can be provided by entering their name and email address. If a non-registered user is invited to perform a review they are given a fast-track link that, if they accept the offer to review the model, registers them as a CoMSES member.
* If a user who has published a model in the Model Library who is not a full CoMSES member accepts the offer to review a model, that user is then registered as a full CoMSES member.
* CoMSES Editor selects N candidates from the pool and clicks a button to send an email to them inviting them to review the model. The existing email templates are currently stored in the DB, accessible via admin/config/comses_settings/modelreviews/templates
* The email invitation offers the candidate a choice to accept or decline the review. If the candidate reviewer declines the review, they can submit additional suggested reviewers (in a single textfield to be shown to the CoMSES Editor).
* If a candidate declines to review, the editor is notified to select a new candidate to invite
* Each reviewer is given `X` days to complete their review.
* A reminder email should be sent to a reviewer after `Y, Y<X` days to remind them to complete their review.
* As each reviewer submits their model review, an email is sent to the Editor Manager, informing them.
* Once all N reviewers have completed their reviews, the Editor is notified that their attention is required on the case.
* Editor reviews case and reviewer recommendations. He/she makes a determination on whether the model certification should be Reviewed, Declined, or Revise and Resubmit and notifies the author with relevant, curated review info.
* If the review is determined to be “Reviewed”, Editor closes case, the model is flagged as peer reviewed, the Editor generates a DOI for the model, and an email is sent informing the author.
* If the review is determined to be “Declined”, the case is closed, and an email is sent to the author notifying them of the decision (NOTE: when will this ever happen?)

Review roles
------------

* all CoMSES Members can submit a codebase release version for review.
* CoMSES Editor manages an individual model review case and finds reviewers for the model
* full CoMSES Members can serve as individual reviewers if they accept the review (excepting the submitter of course)

Review configuration
--------------------

* Number of reviewers
      * integer
      * the default number of reviewers to invite for a model review
* Days to complete review
      * integer
      * the number of days the reviewers have to submit the review before receiving daily notifications