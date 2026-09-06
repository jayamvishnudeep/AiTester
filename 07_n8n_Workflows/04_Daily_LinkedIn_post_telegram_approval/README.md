# Daily QA LinkedIn Post — with Telegram Approval

An n8n workflow that writes a LinkedIn post about software testing every
morning, generates an illustration for it, sends the draft to Telegram for a
look, and publishes it to LinkedIn.

Exported as `Daily QA LinkedIn Post │Agent Hugging face free image generator │Telegram - Working.json`.

## What it does

Every day at **06:30** the workflow runs on its own:

1. **Gemini picks the topic.** A content-strategist agent produces one specific
   topic for a software-testing and AI-in-QA audience, plus a one-line angle
   and the target reader.
2. **OpenAI writes the post.** A second agent turns that into a LinkedIn post,
   a title, hashtags, and a prompt describing an image for the post.
3. **Hugging Face draws the image.** The image prompt is POSTed to Stable
   Diffusion 3 Medium, which returns a PNG.
4. **Telegram shows you the draft.** The post body and hashtags arrive as a
   message with Approve and Disapprove buttons. The workflow pauses here and
   waits for you — it does not run on a timer past this point.
5. **LinkedIn publishes it.** The post goes out publicly with the generated
   image attached.

## The nodes

| Node | Type | Role |
|---|---|---|
| Schedule Trigger | `scheduleTrigger` | Fires daily at 06:30 |
| Content Topic Generator | `agent` | Picks topic, angle, audience |
| Google Gemini Chat Model | `lmChatGoogleGemini` | Brain for the topic agent |
| Structured Output Parser | `outputParserStructured` | Forces `topic` / `angle` / `audience` |
| Content Creator (LinkedIn Post) | `agent` | Writes the post |
| OpenAI Chat Model | `lmChatOpenAi` | Brain for the writer |
| Structured Output Parser2 | `outputParserStructured` | Forces `post_title` / `post_body` / `hash_tags` / `image_prompt` |
| Generate Image (Hugging Face) | `httpRequest` | POST to SD3 Medium, returns PNG |
| Send a text message | `telegram` | `sendAndWait`, Approve / Disapprove |
| Merge | `merge` | Recombines the two branches |
| Create a post | `linkedIn` | Publishes, `PUBLIC`, with image |

## Two things worth explaining

**Why two different models.** Picking a good topic and writing good prose are
different jobs. Gemini handles the first, OpenAI the second. Splitting them also
means the writer receives a narrow brief instead of inventing a subject and
writing about it in the same breath.

**Why the image prompt bans text.** The writer's system message tells it never
to ask for words, labels, numbers or captions inside the picture, and to stay
under twenty words describing one scene — only shapes, icons, arrows,
checkmarks, layered blocks. Free image models render lettering as garbled
nonsense, so a prompt asking for a labelled diagram comes back unusable. Asking
for abstract composition instead is what makes the output publishable.

**Why there is a Merge node.** After the image is generated the run splits: one
branch goes to Telegram to wait for you, the other carries the PNG. The LinkedIn
node needs both the approval and the binary image, so `Merge` (mode `combine`,
by position) puts them back into one item before publishing.

## Writing rules the post follows

Set in the Content Creator's system message:

- No contractions, no emojis
- Plain declarative sentences, short paragraphs
- 150–250 words
- One clear takeaway

## Setting it up

Import the JSON into n8n, then attach five credentials:

| Credential | Used by |
|---|---|
| Google Gemini (`googlePalmApi`) | Google Gemini Chat Model |
| OpenAI (`openAiApi`) | OpenAI Chat Model |
| Header Auth (`httpHeaderAuth`) | Generate Image — your Hugging Face token |
| Telegram (`telegramApi`) | Send a text message |
| LinkedIn OAuth2 (`linkedInOAuth2Api`) | Create a post |

Then change two values to your own, since the export carries the ones from this
account:

- the **chat ID** on the Telegram node — where the draft is sent
- the **person** on the LinkedIn node — the account that publishes

The Hugging Face credential is a Header Auth credential holding your token; the
node sets `Accept: image/png` and sends `{ "inputs": "<image prompt>" }`.

## Notes

- The workflow is exported **active**, so it starts running as soon as it is
  imported and its credentials are attached.
- The Hugging Face inference endpoint is the free tier, which can be slow or
  briefly unavailable when the model is cold.
- A full run takes roughly a minute and a half of processing, plus however long
  the draft sits in Telegram waiting for you.
