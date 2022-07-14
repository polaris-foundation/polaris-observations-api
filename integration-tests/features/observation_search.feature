Feature: Observation set submission
  As a clinician
  I want to search patients observation sets
  So that I can manage patient care

  Background:
    Given the messaging broker is running
    And a valid JWT
    And a patient is admitted to a ward
  
  Scenario: Multiple observation sets are posted for an encounter
    Given an observation set is created for a patient
    When observation count is requested for the encounter
    Then the encounter has 1 observation set
    When another observation set is created for the patient
    And observation count is requested for the encounter
    Then the encounter has 2 observation sets

  Scenario: Latest observation sets for an encounter
    Given an observation set is created for a patient
    When a latest observation set is retrieved for the encounter
    Then the observation set response is correct
    When latest observation sets are retrieved for a list of encounters
    Then the observation set response is correct

  Scenario: Latest observation set gets returned even if earlier observation set is updated
    Given an observation set is created for a patient
    And another observation set is created for the patient
    And observation set 1 is updated
    When a latest observation set is retrieved for the encounter
    Then observation set 2 is returned
    And the observation set response is correct

  Scenario: Observation set search by location
    Given an observation set is created for a patient
    When observation sets are searched for by a location
    Then the observation set exists in the search result
    When observation sets are searched for by a list of locations
    Then the observation set exists in the search result
