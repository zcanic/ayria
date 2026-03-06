# Privacy Boundaries

## Principle

ayria should feel present, not invasive.

## Sensitive Actions

These actions should eventually require explicit policy and likely UI visibility:
- sending screenshots to cloud models
- reading arbitrary local files
- reading clipboard contents
- observing blacklisted apps
- performing desktop automation

## Data Minimization

Store:
- concise summaries when sufficient
- explicit user-approved memories
- task logs needed for debugging

Avoid storing:
- raw screenshots by default forever
- secrets, tokens, passwords
- entire clipboard histories
- sensitive app content from blacklisted contexts

## UI Expectations

The user should be able to answer these questions at any moment:
- what can ayria currently observe
- what did ayria observe recently
- what was sent to a model
- what left the device, if anything
- how to disable a class of observation
