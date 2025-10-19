Short Term:

- chate statter state and response calls should be concurrent. saving state to file should happen after gather
- change event loop to have separate polling for updates, and onchange should cancel the asyncio

Long term:

- Fine tuned models to messages - remove gen z from system prompt probably

Nice to Haves (not needlemoving)

- create a better tester to be able to test independently

Only if necessary:

- change state caching to not be on content

Regarding Refactoring the event loop:

- fix the example chat test script
- ensure consistent handling of the chat name for use in the logging
- modify the logic for action handling to allow splitting chat actions into multiple by new lines

Bugs found in event loop currently:

- the reaction logic sometimes broadens the search beyond the chat, so should select chat each time to avoid this, or stop this extra search
- sometimes the logging does not catch the messages to see they are not new until later, and then fails when there are no new messages
- the default to give a reaction on a skip is bad when there's already a reaction action on the same message, so it fails
