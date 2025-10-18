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

# Guide to the DOM for whatsapp web

## GIFs

For the Emoji, GIFs and Stickers panel click on the button with

- aria-label="Emojis, GIFs, Stickers"
  after click this, click on the button with
- aria-label="Gifs selector"
  then enter the textbox
- aria-label="Search GIFs via Tenor"
  then search for gif.
  Press enter to search for gif, down arrow to move to first gif, then enter to select it and enter to send.

## Attaching images and videos

For atttaching ... click

- aria-label="Attach"
  To attach a photo or video, there is a component
- <input accept="image/*,video/mp4,video/3gpp,video/quicktime" multiple="" type="file" style="display: none;">

## Reply

On a message, upon hover, we gain access to the reaction button to add a reaction to a message, but we also gain access to tthe context menu

- aria-label="Context menu"

The best way to locate the reply button in this context meenu is just seeing the textt in tthe span like

- <span class="x1o2sk6j x6prxxf x6ikm8r x10wlt62 xlyipyv xuxw1ft xpwdb9g">Reply</span>
  Uppon clicking on this (or the <li> that contains it), we can type/paste our message and then

## Typing indicator

For typing indicator to appear, we need to wait after entering text into the input field.
We can also fake typing indicator by typing some text, waiting and then deleting it to makee the dot dot dot typing indicator appear and dissappear.
