## ADDED Requirements

### Requirement: Bot handles photo messages
The bot SHALL process photo messages sent by users in any chat type.

#### Scenario: User sends photo in private chat
- **WHEN** user sends a photo in a private chat
- **THEN** bot downloads the largest available photo size
- **AND** bot forwards to master-agent `/api/image` endpoint
- **AND** bot replies with AI analysis

#### Scenario: User sends photo in group chat
- **WHEN** user sends a photo in a group chat
- **THEN** bot downloads the largest available photo size
- **AND** bot forwards to master-agent with conversation_id `tg_group_{chat_id}`
- **AND** bot replies with AI analysis

### Requirement: Use caption as prompt
The bot SHALL use photo caption as the prompt for image analysis.

#### Scenario: Photo with caption
- **WHEN** user sends a photo with caption "What breed is this dog?"
- **THEN** bot uses the caption as the `prompt` field in API request
- **AND** AI response addresses the specific question

#### Scenario: Photo without caption
- **WHEN** user sends a photo without any caption
- **THEN** bot uses default prompt "What is in this image?"
- **AND** AI provides general image description

### Requirement: Download and encode image
The bot SHALL download the image from Telegram and encode it for the API.

#### Scenario: Successful image download
- **WHEN** bot receives a photo message
- **THEN** bot downloads the largest photo size using `photo[-1].file_id`
- **AND** bot base64-encodes the image bytes
- **AND** bot determines MIME type from file metadata

### Requirement: Handle backend errors gracefully
The bot SHALL handle error conditions with user-friendly messages.

#### Scenario: Backend not configured
- **WHEN** AGENT_API_URL environment variable is not set
- **THEN** bot replies with "AGENT_API_URL is not configured"

#### Scenario: Backend request fails
- **WHEN** HTTP request to master-agent fails (timeout, connection error, non-2xx status)
- **THEN** bot replies with "Backend unavailable, please try again later."

#### Scenario: Image download fails
- **WHEN** Telegram file download fails
- **THEN** bot replies with error message indicating download failure

### Requirement: BackendClient forward_image method
The BackendClient SHALL have a method to forward images to master-agent.

#### Scenario: forward_image sends correct payload
- **WHEN** `forward_image` is called with conversation_id, image_base64, mime_type, prompt, and metadata
- **THEN** method POSTs to `/api/image` with JSON payload matching API spec
- **AND** method uses retry logic for transient failures
- **AND** method returns response dict with `response` field

### Requirement: Bot replies with processed image when available
The bot SHALL check the `/api/image` response for `processed_image_base64` and `processed_image_mime_type` fields and reply with the processed image as a Telegram photo.

#### Scenario: Response contains processed image
- **WHEN** master-agent returns a response with non-null `processed_image_base64` and `processed_image_mime_type`
- **THEN** bot decodes the base64 image
- **AND** bot sends the image via `reply_photo` with the text response as caption
- **AND** caption is truncated to 1024 characters (Telegram limit)

#### Scenario: Response contains no processed image
- **WHEN** master-agent returns a response with `processed_image_base64` as null
- **THEN** bot replies with text only (existing behavior unchanged)

#### Scenario: Processed image with long text response
- **WHEN** master-agent returns a processed image and a text response longer than 1024 characters
- **THEN** bot truncates the caption to 1024 characters
- **AND** the processed image is still sent as a photo

### Requirement: MIME type to filename extension mapping
The bot SHALL derive the correct filename extension from `processed_image_mime_type` when sending processed images.

#### Scenario: PNG processed image
- **WHEN** `processed_image_mime_type` is `image/png`
- **THEN** bot sends photo with filename `processed.png`

#### Scenario: JPEG processed image
- **WHEN** `processed_image_mime_type` is `image/jpeg`
- **THEN** bot sends photo with filename `processed.jpg`

#### Scenario: Unknown MIME type
- **WHEN** `processed_image_mime_type` is not in the known mapping
- **THEN** bot defaults to `.png` extension
