Short Term:

- Split ChatActions into multiple messages - probably just split the text output from llm on newlines into new chatactions
- Better response logic with multiple incoming messages - shouldnt do separate LLM call process for every incoming message - need an incoming buffer time.
- Test new Chate statter flow. (currently now sep llm calls - one API call has react tool + skip tool (+ normal text output ignored), the next is the normal replier LLM with only skip tool, text response used directly) (called async)
- Fix event Loop to handle reacting to same message multiple times
- Tuning of the skip response rates (either better prompt engineering, inc few shot examples or only if this fails look to fine tuning classification models) - skip rate too high for messages bot, state updater and untested for reacter

Long term:

- Fine tuned models to messages - remove gen z from system prompt probably

Nice to Haves (not needlemoving)

- create a better tester to be able to test independently
- Have a set of people to automate - cycles through checking chats every 5s

Only if necessary:

- change state caching to not be on content


Regarding Refactoring the event loop:
- fix the example chat test script
- ensure consistent handling of the chat name for use in the logging
- modify the logic in chate_statter for responding using the logged context + batch messages and split

