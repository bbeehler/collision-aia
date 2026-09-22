# Check and Declare

AIA Canada's web app for collision repair facilities to self-check against the Statement on minimum collision repair requirements, list their OEM and I-CAR credentials, and declare. Credentials are confirmed before a badge is issued. Credentials listed on CPN Auto Body Locator are confirmed automatically; everything else goes to an AIA Canada reviewer.

**Built with:** Streamlit (the app), Supabase (sign-in, database, security rules, screenshot storage), GitHub Actions (hourly automated credential checks), and the Anthropic API (optional AI guidance).

## What's in the repo

| Path | Purpose |
| --- | --- |
| `streamlit_app.py` | App entry point and page navigation |
| `app/views/facility.py` | Shop journey: facility, requirements, credentials, review and gap plan, declare and badge |
| `app/views/verification.py` | Reviewer queue, automated-check results and screenshots, all facilities |
| `app/views/directory.py` | Public directory of facilities with an active badge |
| `app/views/account.py` | Sign in, create account, sign out |
| `app/config.py` | The 27 requirements, programs and who confirms each one |
| `app/logic.py`, `app/db.py`, `app/ai.py`, `app/badge.py` | Status rules, Supabase access, AI guidance, badge |
| `verifier/` | Automated check against CPN Auto Body Locator (headless Chromium) |
| `supabase/migrations/001_check_and_declare.sql` | Tables, security rules, integrity triggers, directory function, evidence bucket |
| `.github/workflows/verify.yml` | Runs the automated check every hour, and on demand |
| `.github/workflows/tests.yml` | Runs the tests on every push |

## Setup

### 1. GitHub
1. Create a new repository, for example `check-and-declare`.
2. Choose **Add file > Upload files** and drag in everything from this folder, including the hidden `.github` and `.streamlit` folders.
3. Commit to `main`.

If your upload skips hidden folders, create them in GitHub with **Add file > Create new file**, typing the path, for example `.github/workflows/verify.yml`, and pasting the contents.

### 2. Supabase
1. Create a project and open **SQL Editor**.
2. Paste in `supabase/migrations/001_check_and_declare.sql` and run it.
3. Go to **Authentication > URL Configuration** and set **Site URL** to your Streamlit app address once you have it (step 4). Confirmation emails link there.
4. Go to **Project Settings > API** and copy three values: the **Project URL**, the **anon public** key and the **service_role** key. The service_role key is only used in GitHub (step 3). Never put it in Streamlit.

### 3. GitHub Actions secrets
In the repository, go to **Settings > Secrets and variables > Actions** and add two secrets:
- `SUPABASE_URL`: the Project URL
- `SUPABASE_SERVICE_ROLE_KEY`: the service_role key

You can also add these optional **Variables** on the same page:
- `AUTO_CONFIRM`: set to `false` to send every automated result to a reviewer during a trial period.
- `RECHECK_DAYS`: how often confirmed credentials are re-checked. The default is 30.
- `LOCATOR_BRANDS`: which programs are checked on the locator, as comma-separated IDs.

Then open the **Actions** tab, enable workflows if asked, and run **Verify credentials** once by hand to confirm it works.

### 4. Streamlit Community Cloud
1. At share.streamlit.io, choose **Create app** and pick the repository, the `main` branch and `streamlit_app.py`.
2. Under **Advanced settings**, choose Python 3.12.
3. In **Secrets**, paste the contents of `.streamlit/secrets.toml.example` with your values filled in:
   - `SUPABASE_URL` and `SUPABASE_ANON_KEY` are required.
   - `ANTHROPIC_API_KEY` turns on AI guidance.
   - `GITHUB_TOKEN` and `GITHUB_REPO` turn on the **Run automated checks now** button. The token should be a fine-grained personal access token with **Actions: read and write** on this repository.
4. Deploy, then copy the app address into Supabase's **Site URL** (step 2.3).

### 5. Make yourself a reviewer
Create an account in the app, then run this in the Supabase SQL Editor:

```sql
insert into public.admins (user_id) select id from auth.users where email = 'you@aiacanada.com';
```

Sign out and back in. The **Verification** page appears.

## How it works

**Shops**
1. Create an account and add a facility.
2. Answer all 27 requirements (yes, no or not sure), with an AI explanation available for each.
3. List their credentials. Answering yes to T2 adds I-CAR Gold Class automatically.
4. Get an AI gap plan for anything unmet.
5. Declare.

The badge and directory listing appear only when every requirement is a yes, the declaration is active, and every credential is confirmed and current.

**Automated checks.** Every hour, GitHub Actions takes each claim for a brand listed on CPN Auto Body Locator (Ford, Stellantis, Kia, Nissan, INFINITI, Toyota, Lexus, Honda, Hyundai, Genesis, Subaru and VinFast) and does the following:
1. Searches the locator by the facility's postal code, then by city.
2. Matches the listing by phone number, street address, name and web domain. A name alone never counts.
3. Reads which brands the shop is certified for.

A strong match on a listed brand is confirmed automatically and re-checked every 30 days. Anything uncertain goes to the reviewer queue with the automated finding attached. Every run is logged with the listing as read and a screenshot of the search.

**Reviewers** handle claims the automated check couldn't confirm, plus GM (Mitchell), I-CAR Gold Class and every other program. For each claim they get:
- a link to the right lookup source
- the last automated result and its screenshot
- Confirm and Couldn't confirm buttons, with a note back to the shop

**Rules the database enforces, whatever the app sends:**
- Only reviewers and the automated check can confirm a credential. A shop editing a claim sends it back to review.
- A declaration is accepted only when all 27 answers are yes. Its dates are set by the server, and shops can only withdraw it.
- Changing any answer away from yes withdraws the active declaration automatically.
- Shops see only their own facilities. The public directory exposes only badge-holding facilities and their public details.

## Tests

```bash
pip install -r requirements.txt -r verifier/requirements.txt pytest
python -m playwright install chromium
python -m pytest -q tests
```

To test the automated check against the live locator for one shop, no database needed:

```bash
python -m verifier.check --name "Shop name" --street "12 Main St" --city Barrie --province ON --postal "L4M 3A1" --phone 7055550101 --brands ford,kia
```

## If the locator changes

The check finds each shop on the results page by its name heading. If none are found, it falls back to each shop's appointment button. If OEC redesigns the site and `verifier.check` stops returning listings, update `EXTRACT_JS` in `verifier/locator.py`.

## Things to know
- Refreshing the browser signs the user out. Streamlit keeps sessions in memory.
- GitHub pauses scheduled workflows in repositories with no activity for 60 days. Any commit, or a manual run, resumes them.
- The app is English-only. `app/config.py` holds all requirement text, ready for a French version.
