## ADDED Requirements

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
