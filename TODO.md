Short Term:

- Test new Chate statter flow. (currently now sep llm calls - one API call has react tool + skip tool (+ normal text output ignored), the next is the normal replier LLM with only skip tool, text response used directly) (called async)
- Fix event Loop to handle reacting to same message multiple times
- Tuning of the skip response rates (either better prompt engineering, inc few shot examples or only if this fails look to fine tuning classification models) - skip rate too high for messages bot, state updater and untested for reacter

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
