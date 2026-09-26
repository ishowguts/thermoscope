# Account setup and prerequisites

You only need to handle account ownership, credentials, final submission and spending decisions. Installation, ingestion, tests and implementation follow once access is ready. Do not send passwords, tokens or API keys in chat.

## 1. NASA FIRMS MAP_KEY — do this first

1. Open [NASA's MAP_KEY page](https://firms.modaps.eosdis.nasa.gov/api/map_key/).
2. Choose **Get MAP_KEY**, enter an email you control and submit the request yourself. NASA says the key is free and sent by email. Check spam if necessary.
3. If the email is already registered, use the page's official `/download` login link to manage/resend the existing key. An Earthdata password is not a FIRMS MAP_KEY.
4. In this fresh `thermoscope` folder, copy `.env.example` to `.env`. Open `.env` locally in your editor and place the key after `FIRMS_MAP_KEY=`. Do not paste it into a shell command, screenshot, task document or frontend setting.
5. Tell the developer only: **“FIRMS key is saved in the local.env.”**

Safe preparation command, run from the fresh repository root (it does not overwrite an existing file):

```sh
test -e .env || cp .env.example .env
chmod 600 .env
```

The acceptance check is one small region/day request, with key-bearing URLs redacted from exceptions and logs. It records product, dates and row counts, never the key. Zero rows can be valid and does not alone prove a failed credential. NASA currently states 5,000 transactions per 10-minute interval; larger requests can consume more than one. This is a quota ceiling, not a target polling rate. [NASA MAP_KEY documentation](https://firms.modaps.eosdis.nasa.gov/api/map_key/)

## 2. NASA Earthdata — needed for archive/HLS paths

1. Open [Earthdata Login](https://urs.earthdata.nasa.gov/) and select **Register for a Profile**, or sign in if you already have an account.
2. Complete the [official registration form](https://urs.earthdata.nasa.gov/users/new) yourself with your name, email, country and actual affiliation. Choose a unique password and keep it in your password manager. Complete any email verification or security challenge shown by NASA.
3. Confirm that you can sign in. Tell the developer only **“Earthdata login works.”** Nobody needs the password in chat or Git.
4. When the HLS/archive provider is chosen, open its official authorization flow and allow only the required application. An account alone does not prove access to every endpoint.
5. The developer will configure the selected official client's supported credential mechanism and test one small authorized download. If a token or protected credential file is required, you enter it locally; it is ignored by Git, permission-restricted and never copied into the repository. Do not pre-generate random tokens or share your main account password.

FIRMS API access and Earthdata login are separate prerequisites. Start the FIRMS path while archive access is being configured. A direct download should validate file type/checksum so an HTML login response cannot be mistaken for satellite data.

## 3. Already available and still needed

| Access | State / next action |
|---|---|
| GitHub `ishowguts` | Connected; new private repository [thermoscope](https://github.com/ishowguts/thermoscope) created. Old sources preserved. |
| SIH team-leader login | You confirmed it is available. Sign in yourself when we verify portal fields. Keep credentials out of project files. |
| Team ID and registered name | Supply non-secret registration details for the cover. Verify nomination/PS choice inside the portal. |
| A frontend contributor | Available according to you. Open this repository and use the shared work contract for assigned tasks. |
| The implementer | Optional. No subscription/API purchase is required to start. |
| Cloud | Choose the provider and billing owner before paid deployment; no machine or billable service has been started. |
| Label review | Arrange a faculty/domain reviewer for difficult examples and another reviewer for adjudicating the test set. We prepare the evidence forms. |

## 4. Access that can wait

- **AlphaEarth:** the documented public cloud-optimized files can be used without making Earth Engine a core dependency. The implementation must still check transfer terms and source attribution.
- **Earth Engine / Dynamic World:** optional experiment. Request access only if this branch is selected; verify eligibility and applicable charges at that time.
- **Copernicus Data Space:** optional imagery provider. Register only if the chosen adapter requires it. Earthdata does not replace Copernicus credentials.
- **Basemap provider:** use a licensed/self-hosted option for offline packs. A public OSM tile URL is not permission to bulk-download tiles.
- **VIIRS Nightfire:** access is licensed; do not pay for it until a specific experiment justifies it. It is not a blocker for the core system.

## 5. A concrete cloud approval request, when needed

Before any paid run, write down the chosen provider/region, resource sizes, data to upload, current price estimate, maximum spend and automatic shutdown/deletion plan. Approve that bounded run, not an unlimited billing permission. The briefing's rupee amounts are planning allowances, not current quotes.

No credentials are needed to read these specifications or prepare the corrected submission narrative. Live ingestion waits for the FIRMS key; imagery experiments wait for their selected provider's access.
