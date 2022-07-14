Feature: Observation set aggregation
  As a clinician
  I want to search patients observation sets
  So that I can manage patient care

  Background:
    Given the messaging broker is running
    And a valid JWT
  
  Scenario: Aggregate observation sets by month report
    Given a patient is admitted to a ward
      And an observation set is created for a patient
      And another observation set is created for the patient
      And observation set aggregation has processed
    When aggregate observation sets by month report requested
    Then aggregate observation sets are returned
    
  Scenario: Aggregate observation sets by location by month report
    Given a patient is admitted to a ward
      And an observation set is created for a patient
      And another observation set is created for the patient
      And observation set aggregation has processed
    When aggregate observation sets by location by month report requested
    Then aggregate location based observation sets are returned
