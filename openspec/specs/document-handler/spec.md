### Requirement: Document messages are forwarded to master-agent
The system SHALL handle Telegram messages that contain a document attachment (any file type). Upon receiving such a message, the bot SHALL download the file from Telegram, base64-encode it, and forward it to the master-agent `/api/document` endpoint along with the filename, MIME type, conversation ID, and Telegram metadata.

#### Scenario: User sends a PDF document
- **WHEN** a user sends a PDF file as a Telegram document message
- **THEN** the bot downloads the file, base64-encodes it, POSTs to master-agent `/api/document` with `mime_type="application/pdf"` and `filename` from the Telegram document object, and replies to the user with the `response` field from the agent's JSON response

#### Scenario: User sends a DOCX document
- **WHEN** a user sends a `.docx` file as a Telegram document message
- **THEN** the bot forwards it to master-agent with `mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"` and replies with the agent response text

#### Scenario: User sends a document with no recognised MIME type
- **WHEN** Telegram reports `document.mime_type` as `None` or an empty string
- **THEN** the bot uses `"application/octet-stream"` as the MIME type and proceeds normally

### Requirement: Document filename is preserved
The system SHALL pass the original Telegram filename (`message.document.file_name`) to master-agent as the `filename` field.

#### Scenario: Telegram provides a filename
- **WHEN** `message.document.file_name` is a non-empty string (e.g., `"report.pdf"`)
- **THEN** the forwarded payload includes `"filename": "report.pdf"`

#### Scenario: Telegram provides no filename
- **WHEN** `message.document.file_name` is `None`
- **THEN** the forwarded payload includes `"filename": "document"` as a safe default

### Requirement: Caption is forwarded as a prompt
The system SHALL include the message caption (if present) in the request payload to master-agent as the `prompt` field.

#### Scenario: Document with caption
- **WHEN** the user attaches a caption such as "Summarise this report" to the document
- **THEN** the forwarded payload includes `"prompt": "Summarise this report"`

#### Scenario: Document without caption
- **WHEN** no caption is attached
- **THEN** the `prompt` field is omitted from the payload

### Requirement: Typing indicator is shown during processing
The system SHALL send a `TYPING` chat action immediately after downloading the document and before calling the backend, to indicate processing activity to the user.

#### Scenario: Typing indicator during document processing
- **WHEN** the bot has downloaded the document and is about to call master-agent
- **THEN** a `ChatAction.TYPING` action is sent to the user's chat

### Requirement: Backend errors are reported to the user
The system SHALL catch backend errors (connection errors, timeouts, non-retryable HTTP errors) and reply to the user with a generic error message rather than crashing silently.

#### Scenario: Master-agent returns a 500 error
- **WHEN** master-agent responds with HTTP 500
- **THEN** the bot replies with the standard "Backend unavailable, please try again later." message

#### Scenario: Master-agent times out
- **WHEN** the request to master-agent exceeds the per-request timeout (120 s)
- **THEN** the bot replies with the standard backend-unavailable message and logs the timeout error

### Requirement: Document handler uses consistent timeout budget with image handler
The system SHALL use a per-request timeout of 120 seconds and a total retry budget of 180 seconds when calling master-agent `/api/document`, matching the image handler configuration.

#### Scenario: Large document triggers extended timeout
- **WHEN** master-agent takes up to 120 seconds to respond
- **THEN** the bot waits for the full duration before considering it a timeout

### Requirement: AGENT_API_URL must be configured for document handling
The system SHALL refuse to process document messages and reply with the standard configuration error message if `AGENT_API_URL` is not set.

#### Scenario: Agent URL not configured
- **WHEN** `AGENT_API_URL` is `None` and a user sends a document
- **THEN** the bot replies with "AGENT_API_URL is not configured" and does not attempt any network call
