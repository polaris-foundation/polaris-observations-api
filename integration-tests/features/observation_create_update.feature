Feature: Observation set submission
  As a clinician
  I want to submit patients observation sets
  So that I can manage patient care

  Background:
    Given the messaging broker is running
    And a valid JWT

  Scenario: Observation set is created and published
    Given a patient is admitted to a ward
    When a new observation set is submitted
    Then the observation set response is correct
      And the observation set is stored
      And a OBSERVATION_SET_UPDATED message is published
      And an ENCOUNTER_UPDATED message is published

  Scenario: Observation set is updated
    Given a patient is admitted to a ward
    And an observation set is created for the patient
    When the observation set is updated
    Then the patch response is correct
  
