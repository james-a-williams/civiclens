# NY BOE Campaign Finance

## Source overview

The New York State Board of Elections (NYSBOE) maintains all itemized campaign finance
disclosure reports filed by candidates and political committees for state races — governor,
attorney general, state assembly, and state senate — from July 1999 to present. This is
the right source for tracking contributions *to* NY state legislators (the people tracked
by the OpenStates connector).

A separate system, the NYC Campaign Finance Board (NYC CFB), covers NYC city races only
(mayor, city council, public advocate). See [NYC CFB notes](#nyc-cfb-alternative) below.

## Data access

**Bulk download (primary path)**
URL: `https://publicreporting.elections.ny.gov/DownloadCampaignFinanceData/DownloadCampaignFinanceData`

Data is delivered as CSV via a form-based download — you select a filer or date range
in the browser and download. There is no open REST API. The domain (`publicreporting.elections.ny.gov`)
returns HTTP 403 to all programmatic requests, so a connector will need to either:

- Submit the download form using a headless browser (Playwright), or
- Reverse-engineer the form POST parameters and replay them with `requests` + browser
  headers to get a direct download URL.

A file format reference PDF exists at:
`https://publicreporting.elections.ny.gov/Content/Help/FileFormatReference.pdf`
(also 403-blocked, but the search snippet confirms it documents CSV position, datatype,
and byte width for each field).

**Coverage:** ~10 million contribution records across all filers, 1999–present.

## Update cadence

Continuous — filers submit disclosures on a rolling basis tied to election calendar
(pre-primary, pre-general, 11-day, 27-day filings, etc.). For pipeline purposes, a
weekly or monthly refresh is reasonable.

## Key tables to load

| Table | Description |
|-------|-------------|
| `contributions` | Monetary and in-kind contributions received by state candidate committees |
| `expenditures` | Disbursements made by candidate committees |
| `filers` | Registered candidate committees and their metadata |

## Schema — contributions (inferred from file format reference snippets + NYSBOE filing forms)

The NYSBOE file format reference documents columns with position, datatype, and byte width.
The fields below are confirmed from search snippets and the NYSBOE electronic filing forms
(CF-02/CF-03); verify exact column names against the FileFormatReference.pdf once you
have browser access to the download page.

| Field | Type | Description |
|-------|------|-------------|
| `filer_id` | bigint | NYSBOE-assigned ID for the candidate committee receiving the contribution |
| `filer_previous_id` | varchar | Legacy filer ID (pre-2013 system) |
| `report_year` | int | Calendar year of the disclosure filing |
| `transaction_code` | varchar | Type of transaction (A = contribution, B = in-kind, etc.) |
| `e_year` | int | Election year this contribution is attributed to |
| `t3_trid` | bigint | Unique transaction ID |
| `date1` | date | Date contribution was received |
| `date2` | date | Date of check (if applicable) |
| `contrib_code` | varchar | Contributor type code (IND = individual, CORP = corporation, PART = partnership, COMM = committee, UNION = labor union, etc.) |
| `contrib_type_code` | varchar | Contribution type (monetary, in-kind, loan) |
| `corp_name` | varchar | Organization/corporate name (populated when contributor is not an individual) |
| `first_name` | varchar | Contributor first name |
| `mid_initial` | varchar | Contributor middle initial |
| `last_name` | varchar | Contributor last name |
| `address` | varchar | Street address |
| `city` | varchar | City |
| `state` | varchar | State (2-letter) |
| `zip` | varchar | ZIP code |
| `check_number` | varchar | Check number |
| `check_date` | date | Check date |
| `amount` | decimal | Contribution amount in USD |
| `amount2` | decimal | In-kind value (if applicable) |
| `description` | varchar | Description of in-kind contribution |
| `occupation` | varchar | Contributor's occupation |
| `emp_name` | varchar | Contributor's employer name |
| `emp_city` | varchar | Employer city |
| `emp_state` | varchar | Employer state |
| `emp_zip` | varchar | Employer ZIP |
| `office_code` | varchar | Office sought by the recipient candidate |
| `district` | varchar | District number |
| `county` | varchar | County |
| `load_at` | timestamp_tz | Added by CivicLens loader |

## Suggested connector structure

```python
class NYBOEConnector(BaseConnector):
    """NY State Board of Elections campaign finance disclosures.

    Covers contributions to and expenditures by NY state candidate committees
    (governor, attorney general, state assembly, state senate).
    Bulk download: https://publicreporting.elections.ny.gov/DownloadCampaignFinanceData/
    """

    SOURCE_NAME = "ny_boe"
    BASE_URL = "https://publicreporting.elections.ny.gov"

    def get_contributions(self, year: int | None = None) -> list[dict]:
        # POST to download form or use Playwright to trigger CSV download
        # Returns list of contribution records as dicts
        ...

    def get_expenditures(self, year: int | None = None) -> list[dict]:
        ...

    def get_filers(self) -> list[dict]:
        # Active/deactive filer list — useful for joining to OpenStates people
        ...

    def fetch_all(self, year: int | None = None) -> dict[str, list[dict]]:
        return {
            "ny_boe_contributions": self.get_contributions(year),
            "ny_boe_expenditures": self.get_expenditures(year),
            "ny_boe_filers": self.get_filers(),
        }
```

## Notes / caveats

- **No open API.** The domain blocks programmatic HTTP access. A Playwright-based approach
  is the most reliable path — load the download page in a headless browser, fill the form,
  and save the CSV response.
- **Volume.** 10M+ contributions across all years. For dev/initial load, scope to a recent
  year (e.g., 2022 or 2024 cycle) rather than doing a full historical load.
- **Filer–legislator join.** NYSBOE filer IDs don't directly match OpenStates person IDs.
  Joining requires a name + district fuzzy match or a manual crosswalk table.
- **Contributor type is the key field.** `contrib_code` distinguishes individuals from
  corporations, unions, PACs, and other committees — this is what enables analysis of
  org/entity contributions.
- **File format reference.** Once you can access the download page in a browser, save
  `FileFormatReference.pdf` and `FileFormatReferenceFiler.pdf` to `docs/sources/` for
  the authoritative column definitions.

---

## NYC CFB alternative

The **NYC Campaign Finance Board** (`nyccfb.info`) is far more developer-friendly:
direct CSV download URLs, documented key files, and data through 2025. However, it covers
**NYC city races only** (mayor, city council, public advocate) — not state assembly or
state senate races. If the project ever adds NYC city officials as a data entity, NYC CFB
is the right source.

Direct contribution download URLs follow this pattern:
`https://www.nyccfb.info/DataLibrary/{YEAR}_Contributions.csv`

Key fields include: `RECIPNAME`, `C_CODE` (contributor type), `NAME`, `AMNT`, `DATE`,
`EMPNAME`, `OCCUPATION`, `STATE`.
