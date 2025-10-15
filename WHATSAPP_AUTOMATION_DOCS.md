# APIs that the WhatsApp Automation will implement

- navigate to chat:
  `navigate_to_chat:(chat_name:str)->None`
  Navigate to the first chat that appears when searching for the term `chat_name`
- read messages on current chat:
  `read_visible_messages:()->list[WhatsappMessage]`
- read image messages
- read voice messages
- send image message
- send voice message
- send message
- read reactions
- react to message

## Wrappers

- send message to chat
  consists of navigate to chat, then send message

## Helper functions for achieving this

- locate chat search bar
- locate message input box
